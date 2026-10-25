"""Celery application and beat schedule (porting-plan 13.1). The schedule is declared here and
loaded into the django-celery-beat database scheduler; every beat task is single-instance."""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("ninefruits")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "admission-expire-drafts": {"task": "admission.expire_drafts", "schedule": crontab(hour=3, minute=10)},
    "registration-release-reserved-seats": {
        "task": "registration.release_reserved_seats",
        "schedule": crontab(minute="*/5"),
    },
    "waitlist-promote": {"task": "registration.promote_waitlists", "schedule": crontab(minute=0)},
    "lms-reconcile": {"task": "lms.reconcile", "schedule": crontab(hour=2, minute=30)},
    "audit-seal": {"task": "audit.seal", "schedule": crontab(hour=3, minute=30)},
    "system-heartbeat": {"task": "core.heartbeat", "schedule": crontab()},
}
