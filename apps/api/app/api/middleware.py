"""Request-ID and security-header middleware.

PHASE.md §Logging and Request IDs (every request carries a request ID) and §Security
(secure HTTP headers, no internal leakage). No PII or secrets are logged here.
"""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.metrics import HTTP_DURATION, HTTP_REQUESTS, HTTP_RESPONSES
from app.core.observability import log_event

REQUEST_ID_HEADER = "X-Request-ID"

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-XSS-Protection": "0",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=(), payment=()",
}
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")


def _new_request_id() -> str:
    return f"req_{uuid.uuid4().hex}"


def _valid_request_id(value: str | None) -> str:
    if not value:
        return _new_request_id()
    candidate = value.strip()
    if (
        not candidate
        or len(candidate) > settings.request_id_max_length
        or _REQUEST_ID_PATTERN.fullmatch(candidate) is None
    ):
        return _new_request_id()
    return candidate


def endpoint_label(path: str) -> str:
    known = {
        "/api/v1/airports",
        "/api/v1/search",
        "/api/v1/schedules/status",
        "/api/v1/health",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/metrics",
    }
    return path if path in known else "other"


def get_request_id(request: Request) -> str:
    """Return the request ID stashed on request.state (falls back to a fresh uuid)."""
    rid = getattr(request.state, "request_id", None)
    return rid if isinstance(rid, str) else _new_request_id()


async def request_context_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Assign a request ID (honoring an inbound X-Request-ID) and set safe headers."""
    inbound = request.headers.get(REQUEST_ID_HEADER)
    request_id = _valid_request_id(inbound)
    request.state.request_id = request_id

    label = endpoint_label(request.url.path)
    started = time.perf_counter()
    HTTP_REQUESTS.labels(method=request.method, endpoint=label).inc()

    content_length = request.headers.get("content-length")
    oversized = False
    if content_length:
        try:
            oversized = int(content_length) > settings.request_body_max_bytes
        except ValueError:
            oversized = True

    # Content-Length is optional (for example, with chunked transfer encoding), so
    # validate the received body as well. The configured bound is intentionally
    # small enough that buffering these API request bodies is safe.
    if not oversized and request.method in {"POST", "PUT", "PATCH"}:
        body = await request.body()
        oversized = len(body) > settings.request_body_max_bytes

    response: Response
    if oversized:
        response = JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "The request body is too large.",
                    "details": None,
                    "request_id": request_id,
                }
            },
        )
    else:
        response = await call_next(request)
    duration = time.perf_counter() - started
    HTTP_DURATION.labels(method=request.method, endpoint=label).observe(duration)
    HTTP_RESPONSES.labels(endpoint=label, status_class=f"{response.status_code // 100}xx").inc()

    response.headers[REQUEST_ID_HEADER] = request_id
    for header, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    response.headers.setdefault("Content-Security-Policy", settings.content_security_policy)
    if settings.hsts_enabled:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    rate_limit = getattr(request.state, "rate_limit", None)
    if rate_limit is not None and rate_limit.enforced:
        response.headers.setdefault("X-RateLimit-Limit", str(rate_limit.limit))
        response.headers.setdefault("X-RateLimit-Remaining", str(rate_limit.remaining))
    log_event(
        "http.request_completed",
        request_id=request_id,
        method=request.method,
        path=label,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 3),
        environment=settings.app_env,
        release=settings.app_release,
    )
    return response
