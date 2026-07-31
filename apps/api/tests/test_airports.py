import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.airports import get_db
from app.db.models import Airport, Base
from app.main import app


@pytest.fixture
def airport_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine)()
    test_session.add(
        Airport(
            code="ATL",
            name="Hartsfield-Jackson Atlanta International Airport",
            city="Atlanta",
            state_or_region="Georgia",
            country_code="US",
            latitude=33.6407,
            longitude=-84.4277,
            timezone="America/New_York",
        )
    )
    test_session.commit()

    def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    test_session.close()
    engine.dispose()


def test_airport_search_returns_atl_by_code(airport_client):
    response = airport_client.get("/api/v1/airports?query=atl")

    assert response.status_code == 200
    assert response.json()["items"][0]["code"] == "ATL"
    assert response.json()["items"][0]["timezone"] == "America/New_York"


def test_airport_search_matches_city_case_insensitively(airport_client):
    response = airport_client.get("/api/v1/airports?query=atlanta&limit=1")

    assert response.status_code == 200
    assert [item["code"] for item in response.json()["items"]] == ["ATL"]


def test_airport_search_validates_limit(airport_client):
    response = airport_client.get("/api/v1/airports?query=atl&limit=51")

    assert response.status_code == 422
