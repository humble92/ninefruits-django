"""Original tests/Feature/Term/ChangeTermStatusTest.php."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from ninefruits.audit.models import ActivityLog
from ninefruits.term.actions import ChangeTermStatus
from ninefruits.term.enums import TermStatus
from tests.factories.term import TermFactory

pytestmark = pytest.mark.django_db


def test_moves_a_term_forward_and_records_it() -> None:
    term = TermFactory()

    ChangeTermStatus()(term, TermStatus.PUBLISHED, "Timetable ready")

    activity = ActivityLog.objects.get(event="term.status_changed")
    term.refresh_from_db()
    assert term.status == TermStatus.PUBLISHED
    assert activity.reason == "Timetable ready"
    assert activity.properties["from"] == "planned"


def test_rejects_transitions_that_skip_steps() -> None:
    with pytest.raises(ValidationError):
        ChangeTermStatus()(TermFactory(), TermStatus.ARCHIVED)


def test_keeps_archived_terms_archived() -> None:
    assert TermStatus.ARCHIVED.allowed_next() == []
