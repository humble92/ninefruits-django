"""Who sees and writes certificate issues: ``CertificateIssue.objects.visible_to`` gives the same
rows as the row level security policies (``db/sql/policies/certificates.sql``) for students,
staff by scope and staff without student record access; writes need ``certificates.issue`` and
a visible student record. Kinds and templates are configuration (no row level security)."""

from __future__ import annotations

from typing import Any

import pytest
from django.db import connection

from ninefruits.certificate.actions import can_issue
from ninefruits.certificate.models import CertificateIssue, CertificateType
from ninefruits.core.db import session_context
from ninefruits.security.actions import AssignRole
from ninefruits.security.enums import Permission, ScopeType
from ninefruits.security.services.authorization import authorization
from tests.factories.certificate import CertificateIssueFactory, CertificateTypeFactory
from tests.factories.organization import OrgUnitFactory, ProgramFactory
from tests.factories.person import StudentRecordFactory
from tests.factories.security import RoleFactory, UserFactory

pytestmark = pytest.mark.django_db


def as_database_user(user: Any) -> None:
    context = session_context()
    context.use_baseline({})
    context.for_user(user.pk)


@pytest.fixture
def world(essential_data: None) -> dict[str, Any]:
    cse, kor = OrgUnitFactory(), OrgUnitFactory()
    alice = StudentRecordFactory(program=ProgramFactory(org_unit=cse))
    bob = StudentRecordFactory(program=ProgramFactory(org_unit=kor))
    kind = CertificateTypeFactory(code="ENR")
    issues = [
        CertificateIssueFactory(student_record=alice, certificate_type=kind),
        CertificateIssueFactory(student_record=alice, certificate_type=kind, revoked=True),
        CertificateIssueFactory(student_record=bob, certificate_type=kind),
    ]

    def scoped(permissions: list[Permission], unit: Any | None = None, user: Any = None) -> Any:
        if user is None:
            user = UserFactory()
        role = RoleFactory(permissions=permissions)
        if unit is None:
            AssignRole()(user, role, "test")
        else:
            AssignRole()(user, role, "test", ScopeType.ORG_UNIT, unit.pk)
        return user

    cse_officer = scoped([Permission.CERTIFICATES_ISSUE])
    scoped([Permission.STUDENT_RECORDS_VIEW], cse, cse_officer)
    users = {
        "alice": UserFactory(person=alice.person),
        "bob": UserFactory(person=bob.person),
        "officer": scoped([Permission.CERTIFICATES_ISSUE, Permission.STUDENT_RECORDS_VIEW]),
        # Issues globally, sees the records of one unit (the role template's way).
        "cse officer": cse_officer,
        # A grant of certificates.issue limited to a unit: the database accepts only global.
        "scoped issuer": scoped([Permission.CERTIFICATES_ISSUE, Permission.STUDENT_RECORDS_VIEW], cse),
        "records viewer": scoped([Permission.STUDENT_RECORDS_VIEW]),
        "kind manager": scoped([Permission.CERTIFICATES_MANAGE]),
        "nobody": UserFactory(),
    }
    authorization().flush()
    return {"users": users, "issues": issues, "alice": alice, "bob": bob, "kind": kind}


def _database_ids() -> set[int]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM certificate_issues")
        return {row[0] for row in cursor.fetchall()}


@pytest.mark.parametrize(
    "who", ["alice", "bob", "officer", "cse officer", "scoped issuer", "records viewer", "kind manager", "nobody"]
)
def test_application_scope_and_row_level_security_agree(world: dict[str, Any], who: str) -> None:
    user = world["users"][who]
    created = {issue.pk for issue in world["issues"]}
    application = set(CertificateIssue.objects.visible_to(user).filter(pk__in=created).values_list("pk", flat=True))
    as_database_user(user)
    database = _database_ids() & created
    assert application == database, who
    expected = {
        "alice": 2,
        "bob": 1,
        "officer": 3,
        "cse officer": 2,
        "scoped issuer": 2,
        "records viewer": 3,
        "kind manager": 0,
        "nobody": 0,
    }[who]
    assert len(database) == expected


def _insert(record: Any, kind: Any, serial: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO certificate_issues (student_record_id, certificate_type_id, locale, serial_number, "
            "verification_code, issued_at) VALUES (%s, %s, 'en', %s, %s, now())",
            [record.pk, kind.pk, serial, serial],
        )
        return int(cursor.rowcount)


def test_writes_need_the_issue_permission_and_a_visible_record(world: dict[str, Any]) -> None:
    from tests.db.support import database_error

    users, alice, bob, kind = world["users"], world["alice"], world["bob"], world["kind"]

    as_database_user(users["cse officer"])
    assert _insert(alice, kind, "RLS-1") == 1
    assert database_error(lambda: _insert(bob, kind, "RLS-2")) is not None

    as_database_user(users["records viewer"])
    assert database_error(lambda: _insert(alice, kind, "RLS-3")) is not None

    # The application refuses what the database would refuse.
    assert can_issue(users["officer"]) and can_issue(users["cse officer"])
    assert not can_issue(users["scoped issuer"])
    as_database_user(users["scoped issuer"])
    assert database_error(lambda: _insert(alice, kind, "RLS-4")) is not None

    as_database_user(users["alice"])
    issue = world["issues"][0]
    with connection.cursor() as cursor:
        cursor.execute("UPDATE certificate_issues SET purpose = 'mine' WHERE id = %s", [issue.pk])
        assert cursor.rowcount == 0
        cursor.execute("DELETE FROM certificate_issues WHERE id = %s", [issue.pk])
        assert cursor.rowcount == 0


def test_kinds_and_templates_are_readable_by_everyone(world: dict[str, Any]) -> None:
    as_database_user(world["users"]["nobody"])
    assert CertificateType.objects.filter(pk=world["kind"].pk).exists()
    assert CertificateType.objects.visible_to(world["users"]["nobody"]).filter(pk=world["kind"].pk).exists()


def test_the_ledger_cannot_be_edited_or_deleted_by_policy(world: dict[str, Any]) -> None:
    officer = world["users"]["officer"]
    issue = world["issues"][0]
    assert officer.has_perm("view_any", CertificateIssue)
    assert officer.has_perm("view", issue)
    assert not officer.has_perm("update", issue)
    assert not officer.has_perm("delete", issue)
    assert not officer.has_perm("create", CertificateIssue)
    # The holder sees the issue and downloads it unless it is revoked.
    alice = world["users"]["alice"]
    assert alice.has_perm("download", issue)
    assert not alice.has_perm("download", world["issues"][1])
    assert officer.has_perm("download", world["issues"][1])
    assert not world["users"]["bob"].has_perm("view", issue)
    # Kinds: reference data viewers look, certificates.manage changes.
    assert world["users"]["kind manager"].has_perm("update", world["kind"])
    assert not officer.has_perm("update", world["kind"])
