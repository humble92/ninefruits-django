"""Which permissions a user has and in which scope (original ``AuthorizationService`` and
``PermissionScope``, ADR 0005).

Sources: active role assignments (role + scope + period) and persona roles. The service is
scoped: one instance per request or Celery task (``begin_scope`` runs on ``request_started``
and ``task_prerun``), so grants are computed once and role changes apply on the next request.
Actions that change roles call ``authorization().flush()``."""

from __future__ import annotations

import contextvars
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from django.db import connection

from ninefruits.security.enums import Permission, ScopeType

from .personas import PersonaResolver, persona_resolver

if TYPE_CHECKING:
    from ninefruits.security.models import User


@dataclass(frozen=True, slots=True)
class PermissionScope:
    """Where a user may use a permission. ``visible_to`` query sets translate this into
    conditions."""

    is_global: bool = False
    org_unit_ids: tuple[int, ...] = field(default_factory=tuple)
    program_ids: tuple[int, ...] = field(default_factory=tuple)
    includes_own: bool = False

    @classmethod
    def none(cls) -> PermissionScope:
        return cls()

    def is_empty(self) -> bool:
        return not self.is_global and not self.org_unit_ids and not self.program_ids and not self.includes_own

    def covers(self, org_unit_id: int, program_id: int) -> bool:
        """Whether a row with this org unit (descendants already expanded) and program is in scope."""
        return self.is_global or org_unit_id in self.org_unit_ids or program_id in self.program_ids

    def merge(self, other: PermissionScope) -> PermissionScope:
        return PermissionScope(
            self.is_global or other.is_global,
            _unique(self.org_unit_ids + other.org_unit_ids),
            _unique(self.program_ids + other.program_ids),
            self.includes_own or other.includes_own,
        )

    @classmethod
    def from_assignment(cls, scope_type: ScopeType | str, scope_id: int | None) -> PermissionScope:
        match ScopeType(scope_type):
            case ScopeType.GLOBAL:
                return cls(is_global=True)
            case ScopeType.ORG_UNIT:
                return cls(org_unit_ids=(int(scope_id or 0),))
            case ScopeType.PROGRAM:
                return cls(program_ids=(int(scope_id or 0),))


def _unique(values: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(dict.fromkeys(values))


def org_unit_descendant_ids(root_ids: list[int] | tuple[int, ...]) -> list[int]:
    """The units and everything below them (``util.org_unit_descendant_ids``; the OrgUnit model
    arrives in Phase 1 and reuses this function)."""
    if not root_ids:
        return []
    with connection.cursor() as cursor:
        cursor.execute("SELECT util.org_unit_descendant_ids(%s::bigint[])", [[int(i) for i in root_ids]])
        row = cursor.fetchone()
    return [int(value) for value in (row[0] if row and row[0] else [])]


class AuthorizationService:
    def __init__(self, personas: PersonaResolver) -> None:
        self.personas = personas
        self._grants: dict[int, dict[str, PermissionScope]] = {}

    def has_permission(self, user: User, permission: Permission | str) -> bool:
        return not self.scope_for(user, permission).is_empty()

    def scope_for(self, user: User, permission: Permission | str) -> PermissionScope:
        return self._grants_for(user).get(str(permission), PermissionScope.none())

    def permission_names(self, user: User) -> list[str]:
        return list(self._grants_for(user).keys())

    def flush(self) -> None:
        self._grants = {}
        self.personas.flush()

    def _grants_for(self, user: User) -> dict[str, PermissionScope]:
        if user.pk is None:
            return {}
        if user.pk in self._grants:
            return self._grants[user.pk]
        if not user.is_active:
            self._grants[user.pk] = {}
            return {}

        from ninefruits.security.models import Permission as PermissionModel
        from ninefruits.security.models import RoleAssignment

        grants: dict[str, PermissionScope] = {}
        rows = (
            RoleAssignment.objects.active()
            .filter(user_id=user.pk, role__permissions__name__isnull=False)
            .values_list("role__permissions__name", "scope_type", "scope_id")
        )
        for name, scope_type, scope_id in rows:
            scope = PermissionScope.from_assignment(scope_type, scope_id)
            grants[name] = grants[name].merge(scope) if name in grants else scope

        # An org unit scope covers the unit and everything below it.
        expanded: dict[tuple[int, ...], tuple[int, ...]] = {}
        for name, scope in list(grants.items()):
            if scope.org_unit_ids:
                roots = tuple(sorted(scope.org_unit_ids))
                if roots not in expanded:
                    expanded[roots] = tuple(org_unit_descendant_ids(roots))
                grants[name] = PermissionScope(scope.is_global, expanded[roots], scope.program_ids, scope.includes_own)

        personas = self.personas.personas_for(user)
        if personas:
            own = PermissionScope(includes_own=True)
            names = (
                PermissionModel.objects.filter(roles__persona__in=[str(p) for p in personas])
                .values_list("name", flat=True)
                .distinct()
            )
            for name in names:
                grants[name] = grants[name].merge(own) if name in grants else own

        self._grants[user.pk] = grants
        return grants

    def users_holding(self, permission: Permission, org_unit_id: int, program_id: int | None = None) -> list[User]:
        """Active users holding the permission through a role assignment whose scope covers the
        org unit and program, e.g. the reviewers to notify."""
        from ninefruits.security.models import RoleAssignment, User

        user_ids = (
            RoleAssignment.objects.active()
            .filter(role__permissions__name=str(permission))
            .values_list("user_id", flat=True)
            .distinct()
        )
        return [
            user
            for user in User.objects.filter(pk__in=list(user_ids), is_active=True).order_by("pk")
            if self.scope_for(user, permission).covers(org_unit_id, program_id or 0)
        ]

    def active_role_names(self, user: User) -> list[str]:
        """Roles the user currently holds through assignments, for display."""
        from ninefruits.security.models import Role, RoleAssignment

        role_ids = RoleAssignment.objects.active().filter(user_id=user.pk).values("role_id")
        return list(Role.objects.filter(pk__in=role_ids).values_list("name", flat=True))


_current: contextvars.ContextVar[AuthorizationService | None] = contextvars.ContextVar(
    "ninefruits_authorization", default=None
)


def authorization() -> AuthorizationService:
    """The scoped service of the current request or task."""
    service = _current.get()
    if service is None:
        service = AuthorizationService(persona_resolver())
        _current.set(service)
    return service


def begin_scope(*args: Any, **kwargs: Any) -> None:
    """Starts a new scope (signal receiver for ``request_started`` and ``task_prerun``)."""
    _current.set(None)
    from .personas import begin_scope as begin_persona_scope

    begin_persona_scope()
