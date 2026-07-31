from fastapi.testclient import TestClient

from app.main import app


def test_security_headers_are_present():
    response = TestClient(app).get("/api/v1/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert (
        response.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    )


def test_openapi_contains_health_endpoints():
    schema = TestClient(app).get("/openapi.json").json()

    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/live" in schema["paths"]
