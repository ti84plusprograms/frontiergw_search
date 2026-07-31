from fastapi.testclient import TestClient

from app.main import app


def test_cors_and_security_headers_are_explicit():
    response = TestClient(app).options(
        "/api/v1/airports?query=atl",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert (
        response.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    )


def test_openapi_contains_airport_and_health_contracts():
    schema = TestClient(app).get("/openapi.json").json()

    assert "/api/v1/airports" in schema["paths"]
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/live" in schema["paths"]
