"""Encryption of secrets the application must read back: TOTP secrets and recovery code seeds
(allauth MFA adapter) and SSO client secrets. The original used Laravel ``encrypt()`` with the
application key; here a Fernet key is derived from ``SECRET_KEY``. Personal data uses the
separate PII keys (``ninefruits.pii``)."""

from __future__ import annotations

import base64
import functools

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings

_PREFIX = "enc:"


@functools.cache
def _fernet(secret_key: str) -> Fernet:
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"ninefruits.security", info=b"secrets").derive(
        secret_key.encode()
    )
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_string(value: str) -> str:
    return _PREFIX + _fernet(settings.SECRET_KEY).encrypt(value.encode()).decode()


def decrypt_string(value: str) -> str:
    """Decrypts a value from ``encrypt_string``. Values without the prefix are returned as they
    are (rows written before encryption)."""
    if not value.startswith(_PREFIX):
        return value
    try:
        return _fernet(settings.SECRET_KEY).decrypt(value[len(_PREFIX) :].encode()).decode()
    except InvalidToken as exception:
        raise ValueError("The value cannot be decrypted with the current SECRET_KEY.") from exception
