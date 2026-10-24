"""Encryption of personal data with the dedicated PII key (original App\\Support\\Pii\\PiiCipher,
Laravel ``Encrypter`` with ``aes-256-gcm``).

The ciphertext format is the original's, so data can move between the two installations with
``pg_dump``/``pg_restore``: ``base64(json({"iv", "value", "mac", "tag"}))`` where ``iv`` is a
12 byte nonce, ``value`` the AES-256-GCM ciphertext, ``tag`` the 16 byte authentication tag
(each base64) and ``mac`` empty (GCM authenticates). Keys are 32 bytes, written ``base64:...``
(or raw text). Previous keys (``PII_PREVIOUS_KEYS``) are still accepted for decryption so data
can be re-encrypted gradually (``pii_reencrypt``)."""

from __future__ import annotations

import base64
import binascii
import json
import os
from functools import lru_cache

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.signals import setting_changed

KEY_BYTES = 32
IV_BYTES = 12
TAG_BYTES = 16


class DecryptError(ValueError):
    """The payload is invalid or no configured key decrypts it."""


class MissingKeyError(RuntimeError):
    pass


def parse_key(key: str, setting: str = "PII_ENCRYPTION_KEY") -> bytes:
    """``base64:...`` keys are decoded; other values are used as they are (original parseKey)."""
    if key == "":
        raise MissingKeyError(f"{setting} is not set. Generate one with: uv run manage.py pii_generate_key")
    if key.startswith("base64:"):
        try:
            return base64.b64decode(key[7:], validate=True)
        except binascii.Error as error:
            raise MissingKeyError(f"{setting} is not valid base64.") from error
    return key.encode()


def _b64decode(value: str) -> bytes:
    # PHP base64_decode is lenient about missing padding.
    return base64.b64decode(value + "=" * (-len(value) % 4))


class PiiCipher:
    def __init__(self, key: str, previous_keys: list[str] | tuple[str, ...] = ()) -> None:
        self._key = self._aead(parse_key(key))
        self._previous = [
            self._aead(parse_key(previous, "PII_PREVIOUS_KEYS")) for previous in previous_keys if previous
        ]

    @staticmethod
    def _aead(key: bytes) -> AESGCM:
        if len(key) != KEY_BYTES:
            raise MissingKeyError("Unsupported cipher or incorrect key length. The PII key must be 32 bytes.")
        return AESGCM(key)

    def encrypt(self, value: str) -> str:
        iv = os.urandom(IV_BYTES)
        sealed = self._key.encrypt(iv, value.encode(), None)
        ciphertext, tag = sealed[:-TAG_BYTES], sealed[-TAG_BYTES:]
        payload = {
            "iv": base64.b64encode(iv).decode(),
            "value": base64.b64encode(ciphertext).decode(),
            "mac": "",
            "tag": base64.b64encode(tag).decode(),
        }
        return base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()

    def decrypt(self, payload: str) -> str:
        return self._decrypt(payload, [self._key, *self._previous])

    def is_encrypted_with_current_key(self, payload: str) -> bool:
        try:
            self._decrypt(payload, [self._key])
        except DecryptError:
            return False
        return True

    @staticmethod
    def _decrypt(payload: str, keys: list[AESGCM]) -> str:
        iv, ciphertext, tag = PiiCipher._parse(payload)
        for key in keys:
            try:
                return key.decrypt(iv, ciphertext + tag, None).decode()
            except InvalidTag:
                continue
        raise DecryptError("Could not decrypt the data.")

    @staticmethod
    def _parse(payload: str) -> tuple[bytes, bytes, bytes]:
        if not isinstance(payload, str):
            raise DecryptError("The payload is invalid.")
        try:
            data = json.loads(_b64decode(payload))
        except (ValueError, binascii.Error) as error:
            raise DecryptError("The payload is invalid.") from error
        if not isinstance(data, dict) or not all(isinstance(data.get(item), str) for item in ("iv", "value", "mac")):
            raise DecryptError("The payload is invalid.")
        if "tag" in data and not isinstance(data["tag"], str):
            raise DecryptError("The payload is invalid.")
        try:
            iv = base64.b64decode(data["iv"], validate=True)
            ciphertext = _b64decode(data["value"])
            tag = _b64decode(data.get("tag") or "")
        except binascii.Error as error:
            raise DecryptError("The payload is invalid.") from error
        if len(iv) != IV_BYTES:
            raise DecryptError("The payload is invalid.")
        if len(tag) != TAG_BYTES:
            raise DecryptError("Could not decrypt the data.")
        return iv, ciphertext, tag


@lru_cache(maxsize=1)
def cipher() -> PiiCipher:
    """The cipher for the configured keys (``PII_ENCRYPTION_KEY``, ``PII_PREVIOUS_KEYS``)."""
    return PiiCipher(settings.PII_ENCRYPTION_KEY, list(settings.PII_PREVIOUS_KEYS))


def _forget_on_setting_change(*, setting: str, **kwargs: object) -> None:
    if setting in ("PII_ENCRYPTION_KEY", "PII_PREVIOUS_KEYS"):
        cipher.cache_clear()


setting_changed.connect(_forget_on_setting_change, dispatch_uid="ninefruits.pii.cipher.reset")
