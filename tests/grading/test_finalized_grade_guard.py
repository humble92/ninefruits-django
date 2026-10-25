"""The database guards finalized grades (original
``tests/Database/Grading/FinalizedGradeGuardTest.php``): ``util.guard_finalized_grade`` refuses
direct changes and deletes, and opens only for an approved, unapplied request of the same
enrollment named in ``app.grade_change_request_id``; the requester cannot decide their own
request (``grade_change_requests_second_person_check``)."""

from __future__ import annotations

from typing import Any

import pytest
from django.db import connection
from django.utils import timezone

from ninefruits.grading.enums import GradeChangeStatus
from ninefruits.grading.models import GradeChangeRequest
from tests.db.support import database_error
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory

pytestmark = pytest.mark.django_db

GUARD = "changes only through an approved grade change request"
SET_REQUEST = "SELECT set_config('app.grade_change_request_id', %s, true)"


@pytest.fixture
def rows(korean_scale: Any) -> dict[str, Any]:
    return {"enrollment": EnrollmentFactory(grade="B0"), "other": EnrollmentFactory(grade="C0")}


def update(enrollment_id: int, sql: str, params: list[Any]) -> int:
    with connection.cursor() as cursor:
        cursor.execute(sql, [*params, enrollment_id])
        return int(cursor.rowcount)


def grade_code(enrollment_id: int) -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT grade_code FROM enrollments WHERE id = %s", [enrollment_id])
        return str(cursor.fetchone()[0])


def approved_request(enrollment: Any, to: str = "A0") -> GradeChangeRequest:
    request = GradeChangeRequest.objects.create(
        enrollment=enrollment,
        from_grade_code=enrollment.grade_code,
        to_grade_code=to,
        reason="Calculation error",
        requested_by=UserFactory(),
        requested_at=timezone.now(),
    )
    request.status = GradeChangeStatus.APPROVED
    request.decided_by = UserFactory()
    request.decided_at = timezone.now()
    request.save()
    return request


CHANGES = {
    "grade": ("UPDATE enrollments SET grade_code = %s, grade_points = %s WHERE id = %s", ["A+", 4.5]),
    "pass flag": ("UPDATE enrollments SET is_passed = %s WHERE id = %s", [False]),
    "back to draft": ("UPDATE enrollments SET grade_status = %s, status = %s WHERE id = %s", ["draft", "enrolled"]),
    "credits": ("UPDATE enrollments SET credits = %s WHERE id = %s", [1]),
    "status": ("UPDATE enrollments SET status = %s WHERE id = %s", ["withdrawn"]),
}


@pytest.mark.parametrize("change", list(CHANGES))
def test_refuses_a_direct_change_to_a_finalized_grade(rows: dict[str, Any], change: str) -> None:
    sql, params = CHANGES[change]
    error = database_error(lambda: update(rows["enrollment"].pk, sql, params))
    assert error is not None and GUARD in error
    assert grade_code(rows["enrollment"].pk) == "B0"


def test_refuses_deleting_a_finalized_enrollment(rows: dict[str, Any]) -> None:
    error = database_error(lambda: update(rows["enrollment"].pk, "DELETE FROM enrollments WHERE id = %s", []))
    assert error is not None and GUARD in error


def test_lets_other_columns_of_a_finalized_enrollment_change(rows: dict[str, Any]) -> None:
    assert (
        update(
            rows["enrollment"].pk, "UPDATE enrollments SET changed_by_id = NULL, updated_at = now() WHERE id = %s", []
        )
        == 1
    )


def test_applies_a_change_only_with_an_approved_unapplied_request_for_the_same_enrollment(rows: dict[str, Any]) -> None:
    enrollment, other = rows["enrollment"], rows["other"]
    request = approved_request(enrollment)
    pending = GradeChangeRequest.objects.create(
        enrollment=other, to_grade_code="A0", reason="x", requested_by=UserFactory(), requested_at=timezone.now()
    )

    def change(request_id: int, enrollment_id: int, grade: str = "A0") -> str | None:
        def run() -> None:
            with connection.cursor() as cursor:
                cursor.execute(SET_REQUEST, [str(request_id)])
            update(enrollment_id, "UPDATE enrollments SET grade_code = %s WHERE id = %s", [grade])

        return database_error(run)

    # A pending request, or an approved one for another enrollment, does not open the guard.
    assert GUARD in (change(pending.pk, other.pk) or "")
    assert GUARD in (change(request.pk, other.pk) or "")
    assert change(request.pk, enrollment.pk) is None
    assert grade_code(enrollment.pk) == "A0"

    # Once applied, the same request does not work again.
    request.applied_at = timezone.now()
    request.save(update_fields=["applied_at"])
    assert GUARD in (change(request.pk, enrollment.pk, "A+") or "")


def test_refuses_a_request_decided_by_its_own_requester(rows: dict[str, Any]) -> None:
    user = UserFactory()
    request = GradeChangeRequest.objects.create(
        enrollment=rows["enrollment"], to_grade_code="A0", reason="x", requested_by=user, requested_at=timezone.now()
    )

    def decide() -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE grade_change_requests SET status = 'approved', decided_by_id = %s, decided_at = now() "
                "WHERE id = %s",
                [user.pk, request.pk],
            )

    error = database_error(decide)
    assert error is not None and "grade_change_requests_second_person_check" in error
