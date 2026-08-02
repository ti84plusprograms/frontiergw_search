from __future__ import annotations

from datetime import time

from app.services.cache_service import CacheService
from tests.fakes import ExplodingRedis, FakeRedis
from tests.routing_fixtures import add_flight, make_source, seed_airports

SEARCH = {"origin": "ATL", "departure_date": "2026-08-04", "max_connections": 0}


def _seed_search(db_session, *, with_result: bool = True):
    seed_airports(db_session)
    source = make_source(db_session, version="synthetic-cache-v1", is_active=True)
    if with_result:
        add_flight(
            db_session,
            source,
            origin="ATL",
            destination="DEN",
            dep=time(9, 0),
            arr=time(10, 30),
        )


def test_search_cache_hit_skips_routing_and_regenerates_metadata(client, db_session, monkeypatch):
    _seed_search(db_session)
    redis = FakeRedis()
    cache = CacheService(redis, enabled=True)  # type: ignore[arg-type]
    monkeypatch.setattr("app.api.search.get_cache_service", lambda: cache)

    import app.api.search as search_api

    original = search_api.search_itineraries
    calls = 0

    def tracked(db, criteria):
        nonlocal calls
        calls += 1
        return original(db, criteria)

    monkeypatch.setattr(search_api, "search_itineraries", tracked)
    first = client.post("/api/v1/search", json=SEARCH)
    second = client.post("/api/v1/search", json=SEARCH)

    assert first.status_code == second.status_code == 200
    assert calls == 1
    first_body = first.json()
    second_body = second.json()
    assert first_body["search_id"] != second_body["search_id"]
    assert first_body["generated_at"] != second_body["generated_at"]
    for body in (first_body, second_body):
        body.pop("search_id")
        body.pop("generated_at")
    assert first_body == second_body


def test_no_result_search_uses_negative_ttl(client, db_session, monkeypatch):
    _seed_search(db_session, with_result=False)
    redis = FakeRedis()
    cache = CacheService(redis, enabled=True)  # type: ignore[arg-type]
    monkeypatch.setattr("app.api.search.get_cache_service", lambda: cache)
    monkeypatch.setattr("app.api.search.settings.no_result_cache_ttl_seconds", 17)

    response = client.post("/api/v1/search", json=SEARCH)
    assert response.status_code == 200
    assert response.json()["result_count"] == 0
    search_keys = [key for key in redis.ttls if key.startswith("search:")]
    assert len(search_keys) == 1
    assert redis.ttls[search_keys[0]] == 17


def test_redis_outage_does_not_fail_search(client, db_session, monkeypatch):
    _seed_search(db_session)
    cache = CacheService(ExplodingRedis(), enabled=True)  # type: ignore[arg-type]
    monkeypatch.setattr("app.api.search.get_cache_service", lambda: cache)
    response = client.post("/api/v1/search", json=SEARCH)
    assert response.status_code == 200
    assert response.json()["result_count"] == 1


def test_schedule_status_is_cached(client, db_session, monkeypatch):
    _seed_search(db_session)
    cache = CacheService(FakeRedis(), enabled=True)  # type: ignore[arg-type]
    monkeypatch.setattr("app.api.schedules.get_cache_service", lambda: cache)
    first = client.get("/api/v1/schedules/status")
    assert first.status_code == 200

    monkeypatch.setattr(
        "app.api.schedules.get_active_schedule_status",
        lambda db: (_ for _ in ()).throw(AssertionError("database must not be queried on hit")),
    )
    second = client.get("/api/v1/schedules/status")
    assert second.status_code == 200
    assert second.json() == first.json()
