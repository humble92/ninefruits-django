"""JSON log formatter binding the request context (request id, user, actor, task id)."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime

from ninefruits.core import context

_SENSITIVE = re.compile(r"(password|secret|token|key|national_id|passport)", re.IGNORECASE)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ctx = context.current()
        payload = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": ctx.request_id,
            "user_id": ctx.user_id,
            "actor": ctx.actor,
        }
        for key, value in getattr(record, "context", {}).items():
            payload[key] = "[redacted]" if _SENSITIVE.search(key) else value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)
