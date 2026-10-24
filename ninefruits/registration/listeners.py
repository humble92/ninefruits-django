"""Event listeners of the registration (original ``DropEnrollment`` dispatching
``PromoteWaitlistJob`` after commit)."""

from __future__ import annotations

from ninefruits.core.events import listen

from .events import EnrollmentDropped


@listen(EnrollmentDropped, after_commit=True)
def promote_waitlist_after_drop(event: EnrollmentDropped) -> None:
    """A freed seat goes to the section's waitlist (a queued task per section)."""
    from .tasks import promote_waitlist

    promote_waitlist.delay(event.enrollment.section_id)
