from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = "postgresql+psycopg://gowild:gowild@localhost:5432/gowild"
    redis_url: str = "redis://localhost:6379/0"
    api_base_url: str = "http://localhost:8000/api/v1"
    frontend_url: str = "http://localhost:3000"
    log_level: str = "INFO"
    schedule_version: str = "unset"
    database_connect_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    redis_connect_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    default_min_connection_minutes: int = Field(default=45, ge=20, le=360)
    default_max_connection_minutes: int = Field(default=240, ge=20, le=360)
    default_max_total_duration_minutes: int = Field(default=720, ge=60, le=1440)
    domestic_estimated_segment_price_usd: Decimal = Field(default=Decimal("14.91"), ge=0)
    international_estimation_enabled: bool = False
    search_cache_ttl_seconds: int = Field(default=3600, gt=0)
    availability_cache_ttl_seconds: int = Field(default=180, gt=0)
    enable_one_stop_search: bool = True
    enable_live_availability: bool = False
    enable_natural_language_search: bool = False
    enable_frontier_browser_automation: bool = False
    enable_search_analytics: bool = True
    enable_international_estimates: bool = False

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_url.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_runtime_settings(self) -> "Settings":
        if self.default_max_connection_minutes <= self.default_min_connection_minutes:
            raise ValueError("default_max_connection_minutes must exceed the minimum")
        if self.app_env != "development":
            if not self.database_url or "gowild:gowild@" in self.database_url:
                raise ValueError("DATABASE_URL must be explicitly configured outside development")
            if not self.redis_url or self.redis_url == "redis://localhost:6379/0":
                raise ValueError("REDIS_URL must be explicitly configured outside development")
        if self.app_env == "production" and self.enable_frontier_browser_automation:
            raise ValueError("Frontier browser automation is not permitted in production")
        return self


settings = Settings()
