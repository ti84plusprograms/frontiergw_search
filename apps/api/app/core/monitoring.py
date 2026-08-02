"""Failure-isolated Sentry initialization and capture helpers."""

from __future__ import annotations

from typing import Any

import sentry_sdk

from app.core.config import settings


def _before_send(event: Any, hint: Any) -> Any:  # noqa: ARG001
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("headers", None)
        request.pop("cookies", None)
        request.pop("data", None)
        request.pop("query_string", None)
    return event


def initialize_monitoring() -> None:
    if not settings.monitoring_enabled or not settings.sentry_dsn:
        return
    try:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            release=settings.app_release,
            send_default_pii=False,
            before_send=_before_send,
            traces_sample_rate=0.0,
        )
    except Exception:
        return


def capture_exception(exc: Exception, request_id: str | None = None) -> None:
    if not settings.monitoring_enabled:
        return
    try:
        with sentry_sdk.push_scope() as scope:
            if request_id:
                scope.set_tag("request_id", request_id)
            scope.set_tag("environment", settings.app_env)
            scope.set_tag("release", settings.app_release)
            sentry_sdk.capture_exception(exc)
    except Exception:
        return
