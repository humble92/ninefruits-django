"""Original tests/Unit/Security/PasswordHashingTest.php. The test settings use a fast hasher, so
this checks the production configuration."""

from __future__ import annotations

from django.contrib.auth.hashers import identify_hasher, make_password
from django.test import override_settings

from config.settings import base


def test_hashes_passwords_with_argon2id() -> None:
    with override_settings(PASSWORD_HASHERS=base.PASSWORD_HASHERS):
        encoded = make_password("Correct-Horse-Battery-9")
        assert encoded.startswith("argon2$argon2id$")
        assert identify_hasher(make_password("x")).algorithm == "argon2"
