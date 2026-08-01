import os
import uuid

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base


@pytest.fixture(scope="session")
def test_db():
    """Create isolated test tables without modifying the application's public schema."""
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

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):  # noqa: ARG001
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        try:
            yield engine
        finally:
            engine.dispose()
        return

    schema = f"gowild_test_{uuid.uuid4().hex}"
    admin_engine = create_engine(db_url, echo=False, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    engine = create_engine(
        db_url,
        echo=False,
        connect_args={"options": f"-csearch_path={schema}"},
    )
    try:
        Base.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()
        with admin_engine.connect() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin_engine.dispose()


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
