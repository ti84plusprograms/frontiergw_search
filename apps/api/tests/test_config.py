from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_documented_runtime_settings_are_loaded():
    settings = Settings(_env_file=None)

    assert settings.default_min_connection_minutes == 45
    assert settings.default_max_connection_minutes == 240
    assert settings.domestic_estimated_segment_price_usd == Decimal("14.91")
    assert settings.enable_frontier_browser_automation is False
    assert settings.allowed_origins == ["http://localhost:3000"]


def test_non_development_settings_require_explicit_service_urls():
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(app_env="production", _env_file=None)


def test_production_disables_browser_automation():
    with pytest.raises(ValidationError, match="browser automation"):
        Settings(
            app_env="production",
            database_url="postgresql+psycopg://service:secret@db.example/gowild",
            redis_url="rediss://cache.example/0",
            enable_frontier_browser_automation=True,
            _env_file=None,
        )
