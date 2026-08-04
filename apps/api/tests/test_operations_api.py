from __future__ import annotations

import pytest

from app.core.config import Settings
from app.services.cache_service import CacheService
from tests.fakes import FakeRedis


def test_request_id_generation_propagation_and_replacement(client):
    generated = client.get("/does-not-exist")
    assert generated.status_code == 404
    assert generated.headers["X-Request-ID"] == generated.json()["error"]["request_id"]

    valid = client.get("/does-not-exist", headers={"X-Request-ID": "trace-123.good"})
    assert valid.headers["X-Request-ID"] == "trace-123.good"
    assert valid.json()["error"]["request_id"] == "trace-123.good"

    invalid = client.get("/does-not-exist", headers={"X-Request-ID": "bad id\nvalue"})
    assert invalid.headers["X-Request-ID"].startswith("req_")
    oversized = client.get("/does-not-exist", headers={"X-Request-ID": "x" * 500})
    assert oversized.headers["X-Request-ID"].startswith("req_")


def test_security_headers_and_request_body_bound(client, monkeypatch):
    response = client.get("/api/v1/health/live")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "payment=()" in response.headers["Permissions-Policy"]

    monkeypatch.setattr("app.api.middleware.settings.request_body_max_bytes", 8)
    too_large = client.post("/api/v1/search", content=b"123456789")
    assert too_large.status_code == 413
    assert too_large.json()["error"]["code"] == "INVALID_REQUEST"
    assert too_large.json()["error"]["request_id"] == too_large.headers["X-Request-ID"]
    assert too_large.headers["X-Content-Type-Options"] == "nosniff"

    # Do not rely on an attacker-controlled or absent Content-Length header.
    mismatched_length = client.post(
        "/api/v1/search", content=b"123456789", headers={"Content-Length": "0"}
    )
    assert mismatched_length.status_code == 413


def test_cors_preflight_also_has_request_id_and_security_headers(client):
    response = client.options(
        "/api/v1/search",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"].startswith("req_")
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_metrics_exposure_is_configurable(client, monkeypatch):
    response = client.get("/metrics")
    assert response.status_code == 200
    for name in (
        "http_requests_total",
        "search_requests_total",
        "cache_hits_total",
        "rate_limit_exceeded_total",
        "schedule_import_failures_total",
        "database_health",
        "database_query_duration_seconds",
    ):
        assert name in response.text

    monkeypatch.setattr("app.main.settings.metrics_enabled", False)
    hidden = client.get("/metrics")
    assert hidden.status_code == 404
    assert hidden.json()["error"]["request_id"] == hidden.headers["X-Request-ID"]


def test_staging_metrics_must_be_disabled_or_protected():
    with pytest.raises(ValueError, match="METRICS_BEARER_TOKEN"):
        Settings(app_env="staging", app_release="release-1", metrics_enabled=True)
    configured = Settings(app_env="staging", app_release="release-1", metrics_enabled=False)
    assert configured.metrics_enabled is False


def test_readiness_requires_database_and_active_schedule(client, monkeypatch):
    monkeypatch.setattr("app.api.health._dependency_status", lambda db: ("error", "degraded", None))
    failed = client.get("/api/v1/health/ready")
    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "DATABASE_UNAVAILABLE"

    monkeypatch.setattr("app.api.health._dependency_status", lambda db: ("ok", "ok", None))
    missing = client.get("/api/v1/health/ready")
    assert missing.status_code == 503
    assert missing.json()["error"]["code"] == "NO_ACTIVE_SCHEDULE"

    monkeypatch.setattr(
        "app.api.health._dependency_status",
        lambda db: ("ok", "degraded", {"version": "synthetic-v1"}),
    )
    degraded = client.get("/api/v1/health/ready")
    assert degraded.status_code == 200
    assert degraded.json() == {
        "status": "degraded",
        "database": "ok",
        "cache": "degraded",
        "schedule_version": "synthetic-v1",
        "release": "development",
    }


def test_airport_rate_limit_uses_standard_error(client, db_session, monkeypatch):
    from tests.test_api_airports import _seed

    _seed(db_session)
    monkeypatch.setattr("app.services.cache_service.settings.rate_limit_enabled", True)
    cache = CacheService(FakeRedis(), enabled=True)  # type: ignore[arg-type]
    monkeypatch.setattr("app.api.airports.get_cache_service", lambda: cache)
    monkeypatch.setattr("app.api.airports.settings.airport_rate_limit_per_minute", 2)
    assert client.get("/api/v1/airports", params={"query": "ATL"}).status_code == 200
    assert client.get("/api/v1/airports", params={"query": "ATL"}).status_code == 200
    limited = client.get(
        "/api/v1/airports",
        params={"query": "ATL"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert limited.status_code == 429
    assert limited.headers["Retry-After"]
    assert "Retry-After" in limited.headers["Access-Control-Expose-Headers"]
    assert limited.json()["error"]["code"] == "RATE_LIMITED"
    assert limited.json()["error"]["request_id"] == limited.headers["X-Request-ID"]
