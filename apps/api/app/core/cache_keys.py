"""Canonical, privacy-preserving cache keys for Phase 5."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.core.config import Settings
from app.schemas.search import SearchCriteria


def _hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def pricing_fingerprint(settings: Settings) -> str:
    return _hash(
        {
            "domestic_segment_price": str(settings.domestic_estimated_segment_price_usd),
            "international_estimation_enabled": settings.international_estimation_enabled,
            "currency": "USD",
        }
    )[:16]


def airport_search_key(settings: Settings, query: str, limit: int) -> str:
    criteria = _hash({"query": query.strip().casefold(), "limit": limit})
    return f"airport:{settings.cache_schema_version}:{criteria}"


def schedule_status_key(settings: Settings) -> str:
    return f"schedule-status:{settings.cache_schema_version}"


def search_key(
    settings: Settings,
    criteria: SearchCriteria,
    *,
    schedule_source: str,
    schedule_version: str,
    max_results: int,
) -> str:
    payload = criteria.model_dump(mode="json")
    payload["max_results"] = max_results
    digest = _hash(payload)
    source = _hash({"source": schedule_source, "version": schedule_version})[:16]
    return (
        f"search:{settings.cache_schema_version}:{settings.routing_algorithm_version}:"
        f"{source}:{pricing_fingerprint(settings)}:{digest}"
    )


def safe_key_id(key: str) -> str:
    """Bounded identifier suitable for logs; never log the full cache key."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
