"""Import types for the admin screens and ``manage.py reference_import <type>`` (original
``ReferenceImporters``). Later phases register their importers (students, instructors,
courses, registration holds) with :func:`register`."""

from __future__ import annotations

from ninefruits.importing.resources import ReferenceResource
from ninefruits.security.enums import Permission

_types: dict[str, type[ReferenceResource]] = {}
_permissions: dict[str, Permission] = {}


def register(resource: type[ReferenceResource], permission: Permission = Permission.REFERENCE_DATA_IMPORT) -> None:
    """Adds an import type. ``permission`` is needed to import it from the admin screens."""
    _types[resource.type_key] = resource
    _permissions[resource.type_key] = permission


def types() -> dict[str, type[ReferenceResource]]:
    _ensure_defaults()
    return dict(_types)


def resource_for(type_key: str) -> type[ReferenceResource] | None:
    _ensure_defaults()
    return _types.get(type_key)


def permission_for(type_key: str) -> Permission:
    _ensure_defaults()
    return _permissions.get(type_key, Permission.REFERENCE_DATA_IMPORT)


_defaults_loaded = False


def _ensure_defaults() -> None:
    # Later phases register from AppConfig.ready(), so a filled registry does not mean the
    # defaults are there.
    global _defaults_loaded
    if _defaults_loaded:
        return
    _defaults_loaded = True
    from ninefruits.importing import importers

    for resource in (
        importers.OrgUnitResource,
        importers.ProgramResource,
        importers.BuildingResource,
        importers.RoomResource,
        importers.LookupValueResource,
    ):
        _types.setdefault(resource.type_key, resource)
        _permissions.setdefault(resource.type_key, Permission.REFERENCE_DATA_IMPORT)
