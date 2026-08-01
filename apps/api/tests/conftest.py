import os

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base


@pytest.fixture(scope="session")
def test_db():
    """Create a test database with migrations applied."""
    db_url = os.getenv(
        "DATABASE_URL_TEST",
        os.getenv("DATABASE_URL", "sqlite:///:memory:"),
    )

    if "sqlite" in db_url:
        # Share one in-memory connection across threads so the FastAPI TestClient
        # (which runs the app in a worker thread) sees the same seeded data.
        engine = create_engine(
            db_url,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(db_url, echo=False)

    # Enable foreign keys for SQLite
    if "sqlite" in db_url:

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):  # noqa: ARG001
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
    else:
        # For PostgreSQL, just create all tables; migrations are validated in CI
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

    return engine


@pytest.fixture
def db_session(test_db):
    """Provide a new database session for each test, with rollback after."""
    connection = test_db.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    try:
        yield session
    finally:
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    """TestClient whose get_db dependency yields the transactional db_session.

    Requests share the test's rolled-back session so API tests stay isolated.
    ``raise_server_exceptions=False`` lets the app's 500 handler run (so we can
    assert the error envelope) instead of re-raising into the test.
    """
    from fastapi.testclient import TestClient

    from app.db.session import get_db
    from app.main import app

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
