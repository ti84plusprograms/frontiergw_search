import os

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.db import Base


@pytest.fixture(scope="session")
def test_db():
    """Create a test database (PostgreSQL if available, SQLite otherwise)."""
    db_url = os.getenv(
        "DATABASE_URL_TEST",
        os.getenv("DATABASE_URL", "sqlite:///:memory:"),
    )

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
