"""Keyed hash for exact match search on encrypted values, stored in ``*_hash`` columns
(original App\\Support\\Pii\\PiiHasher): ``hmac_sha256("<type>:<normalized value>", PII_HASH_KEY)``
in hex, identical to the original so restored data stays searchable."""

from __future__ import annotations

import hashlib
import hmac

from django.conf import settings

from ninefruits.pii.cipher import MissingKeyError, parse_key
from ninefruits.pii.types import PiiType


def pii_hash(value: str, type: PiiType) -> str:
    key = str(settings.PII_HASH_KEY or "")
    if key == "":
        raise MissingKeyError("PII_HASH_KEY is not set. Generate one with: uv run manage.py pii_generate_key")
    message = f"{type.value}:{type.normalize(value)}".encode()
    return hmac.new(parse_key(key, "PII_HASH_KEY"), message, hashlib.sha256).hexdigest()
