"""``pii_generate_key`` (original ``pii:generate-key``): prints new keys. Saves nothing."""

from __future__ import annotations

import base64
import os
from typing import Any

from ninefruits.core.commands import StatusCommand


class Command(StatusCommand):
    help = "Print new keys for PII_ENCRYPTION_KEY and PII_HASH_KEY"

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        self.stdout.write("PII_ENCRYPTION_KEY=base64:" + base64.b64encode(os.urandom(32)).decode())
        self.stdout.write("PII_HASH_KEY=base64:" + base64.b64encode(os.urandom(32)).decode())
        self.stdout.write("")
        self.warn(
            "Changing PII_HASH_KEY invalidates every *_hash search index. Rotate only the encryption key: "
            "move the old key to PII_PREVIOUS_KEYS, then run pii_reencrypt."
        )
        return self.SUCCESS
