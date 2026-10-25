"""``pii_reencrypt`` (original ``pii:reencrypt``): after a key rotation, re-encrypts personal data
still encrypted with a previous key, as a group of Celery tasks."""

from __future__ import annotations

from typing import Any

import questionary
from celery import group
from django.apps import apps
from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.pii.fields import encrypted_pii_fields
from ninefruits.pii.tasks import outdated_fields, reencrypt_records


class Command(AuditedCommand):
    help = "Re-encrypt personal data with the current PII key after a key rotation (Celery tasks)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "model", help="Model with encrypted personal data fields (app_label.Model, e.g. person.Person)"
        )
        parser.add_argument("--chunk", type=int, default=500)
        parser.add_argument("--dry-run", action="store_true", help="Count records still encrypted with a previous key")
        parser.add_argument("--force", action="store_true", help="Do not ask for confirmation")

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        label = str(options["model"])
        try:
            model = apps.get_model(label)
        except LookupError, ValueError:
            model = None
        fields = list(encrypted_pii_fields(model).values()) if model is not None else []
        if model is None or not fields:
            self.error(f"[{label}] is not a model with encrypted personal data fields.")
            return self.FAILURE

        chunk = max(1, int(options["chunk"]))
        if self.is_dry_run():
            outdated = sum(
                1
                for record in model._default_manager.order_by("pk").iterator(chunk_size=chunk)
                if outdated_fields(record, fields)
            )
            self.record_result({"outdated_records": outdated})
            self.info(f"Dry run: {outdated} record(s) still use a previous key.")
            return self.SUCCESS

        if (
            not options["force"]
            and not questionary.confirm(
                f"Re-encrypt every {model._meta.label} record with the current PII key?", default=False
            ).ask()
        ):
            return self.FAILURE

        ids = list(model._default_manager.order_by("pk").values_list("pk", flat=True))
        chunks = [ids[start : start + chunk] for start in range(0, len(ids), chunk)]
        batch_id = None
        if chunks:
            batch_id = group(reencrypt_records.s(model._meta.label_lower, part) for part in chunks).apply_async().id
        self.record_result({"batch_id": batch_id, "jobs": len(chunks)})
        self.info(f"Dispatched batch {batch_id} with {len(chunks)} jobs.")
        return self.SUCCESS
