"""Request-ID and security-header middleware.

PHASE.md §Logging and Request IDs (every request carries a request ID) and §Security
(secure HTTP headers, no internal leakage). No PII or secrets are logged here.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-XSS-Protection": "0",
}


def get_request_id(request: Request) -> str:
    """Return the request ID stashed on request.state (falls back to a fresh uuid)."""
    rid = getattr(request.state, "request_id", None)
    return rid if isinstance(rid, str) else f"req_{uuid.uuid4().hex}"


async def request_context_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Assign a request ID (honoring an inbound X-Request-ID) and set safe headers."""
    inbound = request.headers.get(REQUEST_ID_HEADER)
    request_id = inbound.strip() if inbound and inbound.strip() else f"req_{uuid.uuid4().hex}"
    request.state.request_id = request_id

    response = await call_next(request)

    response.headers[REQUEST_ID_HEADER] = request_id
    for header, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    return response
