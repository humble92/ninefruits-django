"""Child process of the concurrency test (``test_concurrent_registration``). Started with the
``spawn`` method: a fresh interpreter with its own database connection, nothing inherited from
the test process."""

from __future__ import annotations

import os
import time
from typing import Any


def enroll_once(database: str, record_id: int, section_id: int, start_at: float, results: Any) -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
    import django

    django.setup()
    from django.db import connections

    for alias in ("default", "migrator"):
        connections[alias].settings_dict["NAME"] = database

    outcome = "error"
    try:
        from ninefruits.core.db import session_context
        from ninefruits.offering.models import Section
        from ninefruits.person.models import StudentRecord
        from ninefruits.registration.actions import EnrollStudent

        session_context().for_system("test:concurrency")
        record = StudentRecord.objects.get(pk=record_id)
        section = Section.objects.get(pk=section_id)
        engine_warm = EnrollStudent()
        time.sleep(max(0.0, start_at - time.time()))
        result = engine_warm.handle(record, section, None)
        outcome = "enrolled" if result.succeeded() else ("full" if result.refused_for_seat() else "refused")
    except Exception as error:  # reported to the test
        outcome = f"error: {type(error).__name__}: {error}"
    finally:
        results.put((record_id, outcome))
        connections.close_all()
