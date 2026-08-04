"""Per-endpoint client rate limiting with explicit trusted-proxy handling."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from ipaddress import ip_address, ip_network

from starlette.requests import Request

from app.core.config import settings
from app.core.metrics import RATE_LIMITED
from app.core.observability import log_event
from app.services.cache_service import CacheService, RateLimitResult


@dataclass(frozen=True, slots=True)
class RateLimitExceeded(Exception):
    result: RateLimitResult
    endpoint: str


def _trusted(address: str) -> bool:
    try:
        candidate = ip_address(address)
    except ValueError:
        return False
    return any(
        candidate in ip_network(value, strict=False)
        for value in settings.trusted_proxy_networks_list
    )


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    if not _trusted(peer):
        return peer
    forwarded = request.headers.get("x-forwarded-for", "")
    chain = [value.strip() for value in forwarded.split(",") if value.strip()]
    chain.append(peer)
    for value in reversed(chain):
        try:
            ip_address(value)
        except ValueError:
            continue
        if not _trusted(value):
            return value
    return peer


def enforce_rate_limit(
    request: Request,
    *,
    endpoint: str,
    limit: int,
    cache: CacheService,
) -> RateLimitResult:
    address = client_ip(request)
    anonymous = hashlib.sha256(address.encode("utf-8")).hexdigest()[:24]
    result = cache.rate_limit(f"rate:v1:{endpoint}:{anonymous}", limit)
    request.state.rate_limit = result
    if not result.allowed:
        RATE_LIMITED.labels(endpoint=endpoint).inc()
        log_event(
            "rate_limit.exceeded",
            request_id=getattr(request.state, "request_id", None),
            endpoint=endpoint,
            client_ip="redacted",
        )
        raise RateLimitExceeded(result=result, endpoint=endpoint)
    return result
