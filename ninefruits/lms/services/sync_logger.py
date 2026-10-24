"""Wraps one synchronization step in a log row: queued -> succeeded / failed / skipped (original
``SyncLogger``).

The step runs in a savepoint: when it raises, its own writes are rolled back, the log row is
finished as failed with the message (1,000 characters) and the error propagates (the Celery task
retries). The log row itself is written outside the savepoint so the failure stays recorded."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.db import transaction
from django.utils import timezone

from ninefruits.lms.enums import SyncOperation, SyncStatus
from ninefruits.lms.models import LmsPlatform, LmsSyncLog

MESSAGE_MAX = 1000

StepResult = dict[str, Any] | str | None


class SyncLogger:
    def run(
        self,
        platform: LmsPlatform,
        operation: SyncOperation,
        context: dict[str, Any],
        step: Callable[[], StepResult],
        dry_run: bool = False,
        atomic: bool = True,
    ) -> LmsSyncLog:
        """``context``: ``section_id``, ``enrollment_id``, ``user_id``, ``payload`` (all optional).
        ``step`` returns a payload (dict) or a message (str). ``atomic=False`` for a step made of
        logged steps itself (reconcile), whose own log rows must stay when a later one fails."""
        log = LmsSyncLog.objects.create(
            platform=platform,
            section_id=context.get("section_id"),
            enrollment_id=context.get("enrollment_id"),
            user_id=context.get("user_id"),
            operation=operation,
            status=SyncStatus.QUEUED,
            payload=context.get("payload"),
            started_at=timezone.now(),
        )
        if dry_run:
            return self.finish(log, SyncStatus.SKIPPED, "dry run")
        try:
            if atomic:
                with transaction.atomic():
                    result = step()
            else:
                result = step()
        except Exception as error:
            self.finish(log, SyncStatus.FAILED, str(error)[:MESSAGE_MAX])
            raise
        return self.finish(
            log,
            SyncStatus.SUCCEEDED,
            result if isinstance(result, str) else None,
            result if isinstance(result, dict) else None,
        )

    @staticmethod
    def finish(
        log: LmsSyncLog, status: SyncStatus, message: str | None = None, payload: dict[str, Any] | None = None
    ) -> LmsSyncLog:
        log.status = status
        log.message = message
        if payload is not None:
            log.payload = payload
        log.finished_at = timezone.now()
        log.save(update_fields=["status", "message", "payload", "finished_at", "updated_at"])
        return log
