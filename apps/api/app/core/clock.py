"""Single clock boundary for deterministic tests where current time affects behavior."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
