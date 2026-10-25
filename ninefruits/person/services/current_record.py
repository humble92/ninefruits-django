"""The student record a person works with in the portal (original ``CurrentStudentRecord``).

People with several admissions (e.g. a graduate studying again) choose one; the default is the
newest current record, otherwise the newest record. The choice is kept in the session."""

from __future__ import annotations

from typing import Any

from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import StudentRecord

SESSION_KEY = "portal.student_record_id"


class CurrentStudentRecord:
    SESSION_KEY = SESSION_KEY

    def __init__(self, session: Any) -> None:
        self.session = session

    def all(self, user: Any) -> list[StudentRecord]:
        if not getattr(user, "is_authenticated", False) or user.person_id is None:
            return []
        return list(
            StudentRecord.objects.select_related("program", "org_unit")
            .filter(person_id=user.person_id)
            .order_by("-admission_date", "-id")
        )

    def get(self, user: Any) -> StudentRecord | None:
        records = self.all(user)
        chosen_id = self.session.get(SESSION_KEY)
        for record in records:
            if record.pk == chosen_id:
                return record
        for record in records:
            if StudentStatus(record.status).is_active():
                return record
        return records[0] if records else None

    def choose(self, user: Any, record_id: int) -> StudentRecord | None:
        record = next((record for record in self.all(user) if record.pk == int(record_id)), None)
        if record is not None:
            self.session[SESSION_KEY] = record.pk
        return record
