"""Encryption of secrets the application must read back: TOTP secrets and recovery code seeds
(allauth MFA adapter) and SSO client secrets. The original used Laravel ``encrypt()`` with the
application key; here a Fernet key is derived from ``SECRET_KEY``. Personal data uses the
separate PII keys (``ninefruits.pii``).

Key rotation (``operations/security-keys.md``): values written with a key in
``SECRET_KEY_FALLBACKS`` are still read; ``security_reencrypt_secrets`` writes them again with the
current ``SECRET_KEY`` (:func:`reencrypt_string`) before the previous key is removed."""

from __future__ import annotations

import base64
import functools

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
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


def _keys() -> MultiFernet:
    """The current key first (it encrypts), then the fallbacks (they only decrypt)."""
    fallbacks = [key for key in getattr(settings, "SECRET_KEY_FALLBACKS", []) if key]
    return MultiFernet([_fernet(settings.SECRET_KEY), *(_fernet(key) for key in fallbacks)])


def encrypt_string(value: str) -> str:
    return _PREFIX + _fernet(settings.SECRET_KEY).encrypt(value.encode()).decode()


def decrypt_string(value: str) -> str:
    """Decrypts a value from ``encrypt_string``, with the current key or a fallback key. Values
    without the prefix are returned as they are (rows written before encryption)."""
    if not value.startswith(_PREFIX):
        return value
    try:
        return _keys().decrypt(value[len(_PREFIX) :].encode()).decode()
    except InvalidToken as exception:
        raise ValueError("The value cannot be decrypted with SECRET_KEY or SECRET_KEY_FALLBACKS.") from exception


def uses_current_key(value: str) -> bool:
    """Whether ``value`` is plain (nothing to rotate) or encrypted with the current key."""
    if not value.startswith(_PREFIX):
        return True
    try:
        _fernet(settings.SECRET_KEY).decrypt(value[len(_PREFIX) :].encode())
    except InvalidToken:
        return False
    return True


def reencrypt_string(value: str) -> str:
    """``value`` encrypted with the current key (unchanged when it already is). Raises
    ``ValueError`` when no configured key can read it."""
    if uses_current_key(value):
        return value
    return encrypt_string(decrypt_string(value))
