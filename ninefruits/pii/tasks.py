"""Personal data tasks (original App\\Jobs\\Security\\ReencryptPiiRecords)."""

from __future__ import annotations

from typing import Any

from celery import shared_task
from django.apps import apps
from django.db import models

from ninefruits.core.tasks import SystemTask
from ninefruits.pii.cipher import cipher
from ninefruits.pii.fields import EncryptedPiiField, encrypted_pii_fields

CHUNK_SIZE = 500


def outdated_fields(record: models.Model, fields: list[EncryptedPiiField]) -> list[EncryptedPiiField]:
    """Fields of ``record`` still encrypted with a previous key."""
    current = cipher()
    return [
        field
        for field in fields
        if (payload := field.ciphertext(record)) is not None and not current.is_encrypted_with_current_key(payload)
    ]


def reencrypt_record(record: models.Model, fields: list[EncryptedPiiField]) -> bool:
    """Re-encrypts the outdated fields of one record with the current key. The plaintext (and
    therefore the search hash) does not change."""
    changed = outdated_fields(record, fields)
    for field in changed:
        # Assigning the decrypted value encrypts it again with the current key on save.
        setattr(record, field.attname, getattr(record, field.attname))
    if changed:
        record.save(update_fields=[field.name for field in changed])
    return bool(changed)


@shared_task(name="pii.reencrypt_records", base=SystemTask, bind=True)
def reencrypt_records(self: Any, model_label: str, ids: list[int]) -> int:
    """Re-encrypts personal data of the given records that still use a previous PII key.
    Idempotent: records already on the current key are left alone. Returns how many changed."""
    model = apps.get_model(model_label)
    fields = list(encrypted_pii_fields(model).values())
    changed = 0
    queryset = model._default_manager.filter(pk__in=ids).order_by("pk")
    for record in queryset.iterator(chunk_size=CHUNK_SIZE):
        changed += reencrypt_record(record, fields)
    return changed
