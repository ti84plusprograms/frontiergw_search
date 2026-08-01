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

    # --- Phase 4 API configuration (PHASE.md §Security, §Result Limits) ---
    # Comma-separated allowed CORS origins. Never a production wildcard (PHASE.md
    # §Security). Default is the local dev frontend.
    cors_origins: str = "http://localhost:3000"
    # Bounded maximum itineraries returned by POST /api/v1/search. Sorting happens
    # before truncation; truncation is disclosed via a RESULTS_TRUNCATED warning.
    search_max_results: int = 250
    # Airport-search limits (GET /api/v1/airports).
    airport_search_default_limit: int = 10
    airport_search_max_limit: int = 25

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
        if self.search_max_results <= 0:
            raise ValueError("SEARCH_MAX_RESULTS must be positive")
        if self.airport_search_default_limit <= 0:
            raise ValueError("AIRPORT_SEARCH_DEFAULT_LIMIT must be positive")
        if self.airport_search_max_limit < self.airport_search_default_limit:
            raise ValueError("AIRPORT_SEARCH_MAX_LIMIT must be >= AIRPORT_SEARCH_DEFAULT_LIMIT")
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Parsed, trimmed list of allowed CORS origins (empty entries dropped)."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
