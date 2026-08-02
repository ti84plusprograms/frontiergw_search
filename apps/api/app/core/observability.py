"""Structured allowlist logging with centralized redaction."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

_ALLOWED_FIELDS = {
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "environment",
    "release",
    "error_code",
    "origin",
    "departure_date",
    "max_connections",
    "result_count",
    "cache_status",
    "cache_key_id",
    "schedule_version",
    "query_length",
    "client_ip",
    "endpoint",
    "failure_category",
}
_SECRET_WORDS = {
    "authorization",
    "cookie",
    "password",
    "passport",
    "payment",
    "secret",
    "token",
    "database_url",
    "redis_url",
    "sentry_dsn",
    "url",
    "headers",
    "query",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", record.getMessage()),
        }
        fields = getattr(record, "fields", {})
        if isinstance(fields, dict):
            payload.update(redact_fields(fields))
        return json.dumps(payload, sort_keys=True, default=str)


def redact_fields(fields: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in fields.items():
        normalized = key.casefold()
        if normalized in _SECRET_WORDS or normalized not in _ALLOWED_FIELDS:
            continue
        safe[key] = value
    return safe


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    if settings.log_format == "json" or settings.app_env in {"staging", "production"}:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.handlers[:] = [handler]


def log_event(event: str, level: int = logging.INFO, **fields: Any) -> None:
    try:
        logging.getLogger("gowild").log(
            level,
            event,
            extra={"event": event, "fields": redact_fields(fields)},
        )
    except Exception:
        # Observability is never allowed to fail user traffic.
        return
