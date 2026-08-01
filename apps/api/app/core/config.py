from decimal import Decimal, InvalidOperation

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://gowild:gowild@localhost:5432/gowild"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    schedule_version: str = "unset"

    # --- Phase 3 routing engine configuration (PHASE.md §Configuration Requirements) ---
    # Connection-window and duration bounds are inclusive (see ADR-005).
    default_min_connection_minutes: int = 45
    default_max_connection_minutes: int = 240
    default_max_total_duration_minutes: int = 720
    # Estimated GoWild price per itinerary segment. Decimal, never float (PHASE.md
    # §Exact Money Representation). Default from TDD §15.1 / PHASE.md §15.
    domestic_estimated_segment_price_usd: Decimal = Decimal("14.91")
    international_estimation_enabled: bool = False
    # Maximum connections the routing engine will generate. Phase 3 supports 0 or 1;
    # raising this requires an accepted ADR (PHASE.md §Change-Control Rules).
    max_supported_connections: int = 1

    @field_validator("domestic_estimated_segment_price_usd", mode="before")
    @classmethod
    def _parse_price(cls, value: object) -> Decimal:
        # Accept str/int/Decimal from env without going through float, which would
        # reintroduce binary floating-point error into money.
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"invalid decimal price: {value!r}") from exc

    @model_validator(mode="after")
    def _validate_routing_config(self) -> "Settings":
        # Fail clearly at service initialization on invalid routing configuration
        # (PHASE.md §Configuration Requirements).
        if self.default_min_connection_minutes <= 0:
            raise ValueError("DEFAULT_MIN_CONNECTION_MINUTES must be positive")
        if self.default_max_connection_minutes < self.default_min_connection_minutes:
            raise ValueError(
                "DEFAULT_MAX_CONNECTION_MINUTES must be >= DEFAULT_MIN_CONNECTION_MINUTES"
            )
        if self.default_max_total_duration_minutes <= 0:
            raise ValueError("DEFAULT_MAX_TOTAL_DURATION_MINUTES must be positive")
        if self.domestic_estimated_segment_price_usd < 0:
            raise ValueError("DOMESTIC_ESTIMATED_SEGMENT_PRICE_USD must be nonnegative")
        if not 0 <= self.max_supported_connections <= 1:
            raise ValueError("MAX_SUPPORTED_CONNECTIONS must be 0 or 1 in Phase 3")
        return self


settings = Settings()
