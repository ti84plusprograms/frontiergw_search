from __future__ import annotations

from datetime import date

from starlette.requests import Request

from app.core.cache_keys import airport_search_key, search_key
from app.core.config import Settings
from app.schemas.search import SearchCriteria
from app.services.cache_service import CacheService
from app.services.rate_limit import client_ip, enforce_rate_limit
from tests.fakes import ExplodingRedis, FakeRedis


def _request(peer: str, forwarded: str | None = None) -> Request:
    headers = [] if forwarded is None else [(b"x-forwarded-for", forwarded.encode())]
    return Request(
        {"type": "http", "method": "GET", "path": "/", "headers": headers, "client": (peer, 1)}
    )


def test_canonical_cache_keys_normalize_equivalent_inputs():
    config = Settings(cache_schema_version="v7", routing_algorithm_version="r3")
    first = SearchCriteria(origin=" atl ", departure_date=date(2026, 8, 4))
    second = SearchCriteria(origin="ATL", departure_date=date(2026, 8, 4))
    assert search_key(
        config, first, schedule_source="synthetic", schedule_version="1", max_results=25
    ) == search_key(
        config, second, schedule_source="synthetic", schedule_version="1", max_results=25
    )
    assert airport_search_key(config, " ATL ", 10) == airport_search_key(config, "atl", 10)


def test_cache_key_changes_for_schedule_criteria_and_pricing():
    base = Settings(domestic_estimated_segment_price_usd="14.91")
    repriced = Settings(domestic_estimated_segment_price_usd="19.91")
    criteria = SearchCriteria(origin="ATL", departure_date=date(2026, 8, 4))
    key = search_key(
        base, criteria, schedule_source="synthetic", schedule_version="1", max_results=25
    )
    changed_schedule = search_key(
        base, criteria, schedule_source="synthetic", schedule_version="2", max_results=25
    )
    changed_criteria = search_key(
        base,
        criteria.model_copy(update={"max_connections": 0}),
        schedule_source="synthetic",
        schedule_version="1",
        max_results=25,
    )
    changed_price = search_key(
        repriced, criteria, schedule_source="synthetic", schedule_version="1", max_results=25
    )
    assert len({key, changed_schedule, changed_criteria, changed_price}) == 4
    assert "ATL" not in key


def test_json_cache_hit_ttl_corruption_and_invalidation():
    redis = FakeRedis()
    cache = CacheService(redis, enabled=True)  # type: ignore[arg-type]
    assert cache.get_json("search:v1:key", namespace="search").outcome == "MISS"
    assert cache.set_json("search:v1:key", {"results": []}, 300)
    assert redis.ttls["search:v1:key"] == 300
    assert cache.get_json("search:v1:key", namespace="search").value == {"results": []}
    redis.values["search:v1:bad"] = "not-json"
    assert cache.get_json("search:v1:bad", namespace="search").outcome == "CORRUPT"
    assert "search:v1:bad" not in redis.values
    assert cache.invalidate_prefix("search:") == 1


def test_redis_timeout_fails_open_for_cache_and_rate_limit():
    cache = CacheService(ExplodingRedis(), enabled=True)  # type: ignore[arg-type]
    assert cache.get_json("x", namespace="search").outcome == "ERROR"
    result = cache.rate_limit("rate:x", limit=1)
    assert result.allowed is True
    assert result.enforced is False


def test_rate_limit_boundary_and_reset_semantics(monkeypatch):
    monkeypatch.setattr("app.services.cache_service.settings.rate_limit_enabled", True)
    cache = CacheService(FakeRedis(), enabled=True)  # type: ignore[arg-type]
    request = _request("203.0.113.4")
    assert enforce_rate_limit(request, endpoint="search", limit=2, cache=cache).allowed
    assert enforce_rate_limit(request, endpoint="search", limit=2, cache=cache).allowed
    try:
        enforce_rate_limit(request, endpoint="search", limit=2, cache=cache)
    except Exception as exc:
        assert exc.__class__.__name__ == "RateLimitExceeded"
    else:
        raise AssertionError("third request must be rate limited")


def test_rate_limit_is_independent_from_cache_enablement(monkeypatch):
    monkeypatch.setattr("app.services.cache_service.settings.rate_limit_enabled", True)
    cache = CacheService(FakeRedis(), enabled=False)  # type: ignore[arg-type]
    request = _request("203.0.113.5")
    assert enforce_rate_limit(request, endpoint="search", limit=1, cache=cache).enforced
    try:
        enforce_rate_limit(request, endpoint="search", limit=1, cache=cache)
    except Exception as exc:
        assert exc.__class__.__name__ == "RateLimitExceeded"
    else:
        raise AssertionError("cache disablement must not disable rate limiting")


def test_forwarded_header_is_ignored_unless_peer_is_trusted(monkeypatch):
    monkeypatch.setattr("app.services.rate_limit.settings.trusted_proxy_networks", "10.0.0.0/8")
    assert client_ip(_request("203.0.113.10", "198.51.100.9")) == "203.0.113.10"
    assert client_ip(_request("10.0.0.2", "198.51.100.9")) == "198.51.100.9"
