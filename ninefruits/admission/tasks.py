"""Admission tasks. ``admission.expire_drafts`` runs daily at 03:10 (``config/celery.py``, original
``Schedule::command('admission:expire-drafts')->dailyAt('03:10')->withoutOverlapping()->onOneServer()``)."""

from __future__ import annotations

from typing import Any

from celery import shared_task
from django.core.management import call_command

from ninefruits.core.tasks import SystemTask, single_instance


@shared_task(name="admission.expire_drafts", base=SystemTask)
@single_instance("admission.expire_drafts")
def expire_drafts() -> Any:
    """Runs the ``admission_expire_drafts`` command, so the scheduled run is audited like a
    manual one (as the original scheduler did)."""
    return call_command("admission_expire_drafts", verbosity=0)
