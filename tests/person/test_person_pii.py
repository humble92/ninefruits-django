"""Person parts of the original tests/Feature/Security/PersonalDataEncryptionTest.php and
HardeningTest.php ("keeps encrypted identifiers out of arrays"): the national ID and passport
number of people are encrypted, searchable by exact value, masked, never in repr, forms or
serialized plaintext, and re-encrypted after a key rotation."""

from __future__ import annotations

import base64
import json
import os
from io import StringIO
from typing import Any

import pytest
from django.core import serializers
from django.core.management import call_command
from django.db import connection
from django.forms.models import model_to_dict

from ninefruits.person.models import Person
from ninefruits.pii.cipher import cipher
from tests.factories.person import PersonFactory

pytestmark = pytest.mark.django_db


_STORED = {
    "national_id_encrypted": "SELECT national_id_encrypted FROM people WHERE id = %s",
    "passport_number_encrypted": "SELECT passport_number_encrypted FROM people WHERE id = %s",
}


def stored(person: Person, column: str = "national_id_encrypted") -> str | None:
    with connection.cursor() as cursor:
        cursor.execute(_STORED[column], [person.pk])
        row = cursor.fetchone()
    return row[0] if row else None


def test_stores_identity_numbers_encrypted_and_finds_them_by_exact_value() -> None:
    person = PersonFactory(national_id="900101-1234567", passport_number_encrypted="M12345678")
    PersonFactory(national_id="850505-2345678")

    assert "1234567" not in str(stored(person))
    assert "12345678" not in str(stored(person, "passport_number_encrypted"))
    assert Person.objects.get(pk=person.pk).national_id_encrypted == "900101-1234567"
    assert Person.objects.where_pii("national_id", "9001011234567").get().pk == person.pk
    assert Person.objects.where_pii("passport_number", "m12345678").get().pk == person.pk
    assert list(Person.objects.search("900101-1234567").values_list("pk", flat=True)) == [person.pk]


def test_masks_identity_numbers_for_display() -> None:
    person = PersonFactory(national_id="900101-1234567")

    assert person.masked_pii("national_id") == "**********4567"
    assert person.masked_pii("passport_number") is None


def test_keeps_encrypted_identifiers_out_of_repr_forms_and_serialization() -> None:
    person = PersonFactory(national_id="900101-1234567")

    assert "1234567" not in repr(person)
    assert "1234567" not in str(person)
    assert not {"national_id_encrypted", "national_id_hash", "passport_number_encrypted"} & set(model_to_dict(person))
    fields = json.loads(serializers.serialize("json", [person]))[0]["fields"]
    assert "1234567" not in json.dumps(fields)


def test_reencrypts_people_with_a_new_key_after_rotation(settings: Any) -> None:
    person = PersonFactory(national_id="900101-1234567")
    old_key = settings.PII_ENCRYPTION_KEY
    settings.PII_ENCRYPTION_KEY = "base64:" + base64.b64encode(os.urandom(32)).decode()
    settings.PII_PREVIOUS_KEYS = [old_key]
    assert not cipher().is_encrypted_with_current_key(str(stored(person)))

    assert call_command("pii_reencrypt", "person.Person", force=True, chunk=10, stdout=StringIO()) == 0

    assert cipher().is_encrypted_with_current_key(str(stored(person)))
    assert Person.objects.get(pk=person.pk).national_id_encrypted == "900101-1234567"
    assert Person.objects.where_pii("national_id", "9001011234567").exists()
