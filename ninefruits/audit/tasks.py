"""Audit tasks. ``audit.seal`` runs daily at 03:30 (``config/celery.py``, original
``Schedule::command('audit:seal')->dailyAt('03:30')->withoutOverlapping()->onOneServer()``)."""

from __future__ import annotations

from typing import Any

from celery import shared_task
from django.core.management import call_command

from ninefruits.core.tasks import SystemTask, single_instance


@shared_task(name="audit.seal", base=SystemTask)
@single_instance("audit.seal")
def seal() -> Any:
    """Runs the ``audit_seal`` command, so the scheduled run is audited like a manual one."""
    return call_command("audit_seal", verbosity=0)
