"""Progress of a batch of Celery tasks (original Laravel ``Bus::batch`` and its ``job_batches``
table, porting-plan 13.1). A chord's header tasks each report when they finish or fail; the
chord's callback finishes the batch. Screens show ``progress()``.

    batch = JobBatch.start("term-close:2026-FA", total=len(chunks), options={"term_id": term.pk})
    chord(close_term_records.s(batch.id, ...) for ...)(finish_term_close.s(batch.id, ...))

Timestamps are Unix seconds, as in the original table."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Self

from django.db import models
from django.db.models import F


def _now() -> int:
    return int(time.time())


class JobBatchQuerySet(models.QuerySet["JobBatch"]):
    def named(self, prefix: str) -> Self:
        return self.filter(name__startswith=prefix)

    def running(self) -> Self:
        return self.filter(finished_at__isnull=True, cancelled_at__isnull=True)

    def visible_to(self, user: Any) -> Self:
        return self


class JobBatch(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=255)
    total_jobs = models.IntegerField()
    pending_jobs = models.IntegerField()
    failed_jobs = models.IntegerField()
    #: JSON list of the failed task ids.
    failed_job_ids = models.TextField()
    #: JSON object: what the batch is about (e.g. the term), shown to staff.
    options = models.TextField(null=True, blank=True)
    cancelled_at = models.IntegerField(null=True, blank=True)
    created_at = models.IntegerField()
    finished_at = models.IntegerField(null=True, blank=True)

    objects = JobBatchQuerySet.as_manager()

    class Meta:
        db_table = "job_batches"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    @classmethod
    def start(cls, name: str, total: int, options: dict[str, Any] | None = None) -> JobBatch:
        return cls.objects.create(
            id=str(uuid.uuid4()),
            name=name,
            total_jobs=total,
            pending_jobs=total,
            failed_jobs=0,
            failed_job_ids="[]",
            options=json.dumps(options or {}),
            created_at=_now(),
        )

    @classmethod
    def job_done(cls, batch_id: str) -> None:
        cls.objects.filter(pk=batch_id, pending_jobs__gt=0).update(pending_jobs=F("pending_jobs") - 1)

    @classmethod
    def job_failed(cls, batch_id: str, task_id: str | None) -> None:
        batch = cls.objects.filter(pk=batch_id).first()
        if batch is None:
            return
        failed = [*batch.failed_ids(), *([task_id] if task_id else [])]
        cls.objects.filter(pk=batch_id).update(failed_jobs=F("failed_jobs") + 1, failed_job_ids=json.dumps(failed))

    @classmethod
    def finish(cls, batch_id: str) -> None:
        cls.objects.filter(pk=batch_id).update(finished_at=_now())

    @classmethod
    def cancel(cls, batch_id: str) -> None:
        cls.objects.filter(pk=batch_id, cancelled_at__isnull=True).update(cancelled_at=_now())

    def failed_ids(self) -> list[str]:
        try:
            return [str(value) for value in json.loads(self.failed_job_ids or "[]")]
        except ValueError:
            return []

    def option(self, name: str) -> Any:
        try:
            return json.loads(self.options or "{}").get(name)
        except ValueError:
            return None

    def processed(self) -> int:
        return self.total_jobs - self.pending_jobs

    def progress(self) -> int:
        """Percent of the jobs done (0-100)."""
        return 100 if self.total_jobs == 0 else int(self.processed() * 100 / self.total_jobs)

    @property
    def is_finished(self) -> bool:
        return self.finished_at is not None

    @property
    def is_cancelled(self) -> bool:
        return self.cancelled_at is not None

    @property
    def has_failures(self) -> bool:
        return self.failed_jobs > 0
