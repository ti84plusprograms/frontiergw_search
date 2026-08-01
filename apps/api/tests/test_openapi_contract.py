"""Contract tests: OpenAPI generation + committed openapi.json freshness."""

from __future__ import annotations

import json
from pathlib import Path

from app.main import app

OPENAPI_PATH = Path(__file__).resolve().parent.parent / "openapi.json"


def test_openapi_generation_succeeds():
    schema = app.openapi()
    assert schema["openapi"].startswith("3.")
    paths = set(schema["paths"])
    assert {"/api/v1/airports", "/api/v1/search", "/api/v1/schedules/status"} <= paths


def test_committed_openapi_is_fresh():
    """The committed openapi.json must match the current app schema (regen if this fails)."""
    current = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    committed = OPENAPI_PATH.read_text()
    assert committed == current, "openapi.json is stale — run scripts/export_openapi.py"


def test_public_error_and_enum_values_stable():
    schema = app.openapi()
    components = schema.get("components", {}).get("schemas", {})
    # Public enums the frontend depends on must exist with stable values.
    sort = components.get("SortMode", {}).get("enum", [])
    assert set(sort) == {
        "PRICE",
        "TOTAL_DURATION",
        "EARLIEST_DEPARTURE",
        "LATEST_DEPARTURE",
        "DESTINATION",
    }
    err = components.get("ApiErrorCode", {}).get("enum", [])
    assert "INVALID_REQUEST" in err and "NO_ACTIVE_SCHEDULE" in err
