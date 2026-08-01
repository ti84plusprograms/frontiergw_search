"""Safety regression for the PostgreSQL test database fixture."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text


def test_postgresql_tests_use_an_isolated_schema(db_session):
    db_url = os.getenv("DATABASE_URL_TEST", os.getenv("DATABASE_URL", "sqlite:///:memory:"))
    if "sqlite" in db_url:
        pytest.skip("PostgreSQL-only test-schema assertion")

    schema = db_session.execute(text("select current_schema()"), execution_options={}).scalar_one()
    assert schema.startswith("gowild_test_")
    assert schema != "public"
