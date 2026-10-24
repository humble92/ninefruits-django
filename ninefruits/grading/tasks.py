"""Term close tasks (original ``CloseTermRecordsJob`` in a ``Bus::batch`` chained to
``FinishTermCloseJob``; porting-plan 10 "학기 마감 배치" and 13.1). ``CloseTerm.close`` starts a
chord: one ``grading.close_term_records`` per chunk of students, then
``grading.finish_term_close``. Progress is the ``job_batches`` row; a chunk that keeps failing
after its retries marks the batch failed and the finish does not run (start the close again
after fixing the cause: chunks are idempotent)."""

from __future__ import annotations

from typing import Any

from celery import shared_task
from django.db import DatabaseError

from ninefruits.core.batches import JobBatch
from ninefruits.core.tasks import SystemTask

#: Retries of a chunk on database errors (deadlocks, a lost connection), with backoff.
MAX_RETRIES = 3


@shared_task(
    name="grading.close_term_records",
    base=SystemTask,
    bind=True,
    max_retries=MAX_RETRIES,
    default_retry_delay=10,
)
def close_term_records(self: Any, batch_id: str, term_id: int, record_ids: list[int]) -> int:
    """Term records, standing and honors eligibility for a chunk of students."""
    from ninefruits.grading.actions import CloseTerm
    from ninefruits.term.models import Term

    batch = JobBatch.objects.filter(pk=batch_id).first()
    if batch is not None and batch.is_cancelled:
        return 0
    try:
        count = CloseTerm().close_records(Term.objects.select_related("term_type").get(pk=term_id), record_ids)
    except DatabaseError as error:
        if self.request.retries < MAX_RETRIES and not self.request.is_eager:
            raise self.retry(exc=error, countdown=10 * 2**self.request.retries) from error
        JobBatch.job_failed(batch_id, self.request.id)
        raise
    except Exception:
        JobBatch.job_failed(batch_id, self.request.id)
        raise
    JobBatch.job_done(batch_id)
    return count


@shared_task(name="grading.finish_term_close", base=SystemTask)
def finish_term_close(batch_id: str, term_id: int, user_id: int | None, reason: str | None) -> dict[str, int] | None:
    """Last step, after every student's record: honors ranks, the records become the official
    snapshot, the term moves to grades closed; the staff member who started it is told."""
    from ninefruits.core.events import dispatch
    from ninefruits.grading.actions import CloseTerm
    from ninefruits.grading.events import TermClosed
    from ninefruits.grading.notifications import send_term_closed
    from ninefruits.security.models import User
    from ninefruits.term.models import Term

    batch = JobBatch.objects.filter(pk=batch_id).first()
    if batch is not None and (batch.is_cancelled or batch.has_failures):
        return None
    term = Term.objects.get(pk=term_id)
    staff = User.objects.filter(pk=user_id).first() if user_id is not None else None
    counts = CloseTerm().finish(term, staff, reason)
    JobBatch.finish(batch_id)
    dispatch(TermClosed(term, counts))
    send_term_closed(staff, term, counts)
    return counts
