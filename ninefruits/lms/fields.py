"""Encrypted JSON column (original Laravel cast ``encrypted:array``).

The value is a dict in Python and ciphertext in the database (a ``text`` column): the JSON text
encrypted with the PII cipher (``ninefruits.pii.cipher``, AES-256-GCM with ``PII_ENCRYPTION_KEY``;
previous keys still decrypt). An unchanged value keeps its stored ciphertext on save, so saving a
row for another reason does not produce a spurious data audit entry. The value never appears in
serializers (``dumpdata`` gets the ciphertext), ``__repr__`` or admin lists, and the data audit
trigger treats the column as secret (``util.enable_audit(..., ARRAY['credentials'])``)."""

from __future__ import annotations

import json
from typing import Any

from django.db import models

from ninefruits.pii.cipher import cipher


class DecryptedDict(dict[str, Any]):
    """A value read from the database: remembers its ciphertext and the original content."""

    __slots__ = ("ciphertext", "original")

    def __init__(self, data: dict[str, Any], ciphertext: str) -> None:
        super().__init__(data)
        self.ciphertext = ciphertext
        self.original = json.dumps(data, sort_keys=True)

    def is_unchanged(self) -> bool:
        return json.dumps(dict(self), sort_keys=True) == self.original


class EncryptedJSONField(models.TextField):  # type: ignore[type-arg]
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> Any:
        name, path, args, kwargs = super().deconstruct()
        for key in ("null", "blank"):
            if kwargs.get(key) is True:
                kwargs.pop(key)
        return name, path, args, kwargs

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        if value is None:
            return None
        data = json.loads(cipher().decrypt(str(value)))
        return DecryptedDict(data if isinstance(data, dict) else {"value": data}, str(value))

    def to_python(self, value: Any) -> Any:
        if value is None or isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip().startswith("{"):
            return json.loads(value)
        return value

    def get_prep_value(self, value: Any) -> Any:
        if value is None or value == {} or value == "":
            return None
        if hasattr(value, "resolve_expression"):
            return value
        if isinstance(value, DecryptedDict) and value.is_unchanged():
            return value.ciphertext
        return cipher().encrypt(json.dumps(dict(value), separators=(",", ":"), ensure_ascii=False))

    def value_to_string(self, obj: models.Model) -> str:
        stored = self.get_prep_value(self.value_from_object(obj))
        return "" if stored is None else str(stored)
