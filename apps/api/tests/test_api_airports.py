"""API-001 airport search endpoint tests. Runs on SQLite (no arrays/partial index)."""

from __future__ import annotations

from app.db.models.airport import Airport


def _seed(db):
    # SYNTHETIC TEST airports, incl. two sharing the city text "Orlando".
    rows = [
        Airport(
            code="ATL",
            name="Hartsfield-Jackson Atlanta International",
            city="Atlanta",
            state_or_region="Georgia",
            country_code="US",
            latitude=33.6,
            longitude=-84.4,
            timezone="America/New_York",
        ),
        Airport(
            code="MCO",
            name="Orlando International",
            city="Orlando",
            state_or_region="Florida",
            country_code="US",
            latitude=28.4,
            longitude=-81.3,
            timezone="America/New_York",
        ),
        Airport(
            code="ORL",
            name="Orlando Executive",
            city="Orlando",
            state_or_region="Florida",
            country_code="US",
            latitude=28.5,
            longitude=-81.3,
            timezone="America/New_York",
        ),
        Airport(
            code="DEN",
            name="Denver International",
            city="Denver",
            state_or_region="Colorado",
            country_code="US",
            latitude=39.8,
            longitude=-104.6,
            timezone="America/Denver",
        ),
        Airport(
            code="XXX",
            name="Inactive Field",
            city="Nowhere",
            state_or_region=None,
            country_code="US",
            latitude=1.0,
            longitude=1.0,
            timezone="America/New_York",
            is_active=False,
        ),
    ]
    for row in rows:
        db.add(row)
    db.flush()


def test_exact_code_match_ranks_first(client, db_session):
    _seed(db_session)
    resp = client.get("/api/v1/airports", params={"query": "atl"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 1
    assert body["items"][0]["code"] == "ATL"
    # Public shape: no internal fields (latitude/longitude/is_active).
    assert set(body["items"][0]) == {
        "code",
        "name",
        "city",
        "state_or_region",
        "country_code",
        "timezone",
    }


def test_case_insensitive(client, db_session):
    _seed(db_session)
    lower = client.get("/api/v1/airports", params={"query": "ATL"}).json()
    upper = client.get("/api/v1/airports", params={"query": "atl"}).json()
    assert lower["items"][0]["code"] == upper["items"][0]["code"] == "ATL"


def test_city_match_returns_both_orlando(client, db_session):
    _seed(db_session)
    body = client.get("/api/v1/airports", params={"query": "orlando"}).json()
    codes = {i["code"] for i in body["items"]}
    assert {"MCO", "ORL"} <= codes


def test_name_match(client, db_session):
    _seed(db_session)
    body = client.get("/api/v1/airports", params={"query": "denver international"}).json()
    assert body["items"][0]["code"] == "DEN"


def test_inactive_excluded(client, db_session):
    _seed(db_session)
    body = client.get("/api/v1/airports", params={"query": "nowhere"}).json()
    assert all(i["code"] != "XXX" for i in body["items"])


def test_limit_applied(client, db_session):
    _seed(db_session)
    body = client.get("/api/v1/airports", params={"query": "o", "limit": 1}).json()
    assert len(body["items"]) == 1
    assert body["count"] == 1


def test_limit_too_high_is_422(client, db_session):
    _seed(db_session)
    resp = client.get("/api/v1/airports", params={"query": "atl", "limit": 100})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_REQUEST"
    assert resp.headers["X-Request-ID"]


def test_limit_zero_is_422(client, db_session):
    _seed(db_session)
    assert client.get("/api/v1/airports", params={"query": "atl", "limit": 0}).status_code == 422


def test_empty_query_is_422(client, db_session):
    _seed(db_session)
    resp = client.get("/api/v1/airports", params={"query": ""})
    assert resp.status_code == 422


def test_whitespace_only_query_is_422(client, db_session):
    _seed(db_session)
    resp = client.get("/api/v1/airports", params={"query": "   "})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_REQUEST"


def test_deterministic_repeated(client, db_session):
    _seed(db_session)
    a = client.get("/api/v1/airports", params={"query": "o"}).json()
    b = client.get("/api/v1/airports", params={"query": "o"}).json()
    assert [i["code"] for i in a["items"]] == [i["code"] for i in b["items"]]
