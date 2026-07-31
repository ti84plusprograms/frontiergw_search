from fastapi.testclient import TestClient

from app.api import health as health_api
from app.main import app


class HealthyDatabase:
    def execute(self, _statement):
        return None

    def close(self):
        return None


class HealthyCache:
    def ping(self):
        return True


def test_liveness_does_not_require_dependencies():
    response = TestClient(app).get("/api/v1/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_ok_when_dependencies_are_healthy(monkeypatch):
    monkeypatch.setattr(health_api, "SessionLocal", lambda: HealthyDatabase())
    monkeypatch.setattr(health_api, "get_redis", lambda: HealthyCache())

    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"
    assert response.json()["cache"] == "ok"


def test_health_returns_service_unavailable_when_database_fails(monkeypatch):
    def fail_database():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(health_api, "SessionLocal", fail_database)
    monkeypatch.setattr(health_api, "get_redis", lambda: HealthyCache())

    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "database": "error",
        "cache": "ok",
        "schedule_version": "unset",
    }


def test_health_returns_service_unavailable_when_cache_fails(monkeypatch):
    monkeypatch.setattr(health_api, "SessionLocal", lambda: HealthyDatabase())

    def fail_cache():
        raise RuntimeError("cache unavailable")

    monkeypatch.setattr(health_api, "get_redis", fail_cache)

    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["database"] == "ok"
    assert response.json()["cache"] == "error"
