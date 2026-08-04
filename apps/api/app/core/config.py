from decimal import Decimal, InvalidOperation
from ipaddress import ip_network

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_release: str = "development"
    database_url: str = "postgresql+psycopg://gowild:gowild@localhost:5432/gowild"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    log_format: str = "console"
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

    # --- Phase 5 caching and resilience ---
    cache_enabled: bool = True
    cache_schema_version: str = "v1"
    routing_algorithm_version: str = "v1"
    airport_search_cache_ttl_seconds: int = 21600
    schedule_status_cache_ttl_seconds: int = 300
    search_cache_ttl_seconds: int = 1800
    same_day_search_cache_ttl_seconds: int = 300
    no_result_cache_ttl_seconds: int = 300
    cache_error_backoff_seconds: int = 30
    cache_operation_timeout_ms: int = 100
    cache_lock_ttl_seconds: int = 10

    # Rate limits use Redis and fail open when it is unavailable.
    rate_limit_enabled: bool = True
    airport_rate_limit_per_minute: int = 120
    search_rate_limit_per_minute: int = 30
    schedule_status_rate_limit_per_minute: int = 60
    trusted_proxy_networks: str = ""

    # Monitoring and security.
    monitoring_enabled: bool = False
    sentry_dsn: str = ""
    metrics_enabled: bool = True
    metrics_bearer_token: str = ""
    request_body_max_bytes: int = 65536
    request_id_max_length: int = 128
    airport_query_max_length: int = 100
    content_security_policy: str = (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    )
    hsts_enabled: bool = False

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
        positive_fields = {
            "AIRPORT_SEARCH_CACHE_TTL_SECONDS": self.airport_search_cache_ttl_seconds,
            "SCHEDULE_STATUS_CACHE_TTL_SECONDS": self.schedule_status_cache_ttl_seconds,
            "SEARCH_CACHE_TTL_SECONDS": self.search_cache_ttl_seconds,
            "SAME_DAY_SEARCH_CACHE_TTL_SECONDS": self.same_day_search_cache_ttl_seconds,
            "NO_RESULT_CACHE_TTL_SECONDS": self.no_result_cache_ttl_seconds,
            "CACHE_ERROR_BACKOFF_SECONDS": self.cache_error_backoff_seconds,
            "CACHE_OPERATION_TIMEOUT_MS": self.cache_operation_timeout_ms,
            "CACHE_LOCK_TTL_SECONDS": self.cache_lock_ttl_seconds,
            "AIRPORT_RATE_LIMIT_PER_MINUTE": self.airport_rate_limit_per_minute,
            "SEARCH_RATE_LIMIT_PER_MINUTE": self.search_rate_limit_per_minute,
            "SCHEDULE_STATUS_RATE_LIMIT_PER_MINUTE": self.schedule_status_rate_limit_per_minute,
            "REQUEST_BODY_MAX_BYTES": self.request_body_max_bytes,
            "REQUEST_ID_MAX_LENGTH": self.request_id_max_length,
            "AIRPORT_QUERY_MAX_LENGTH": self.airport_query_max_length,
        }
        for name, value in positive_fields.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if not self.cache_schema_version.strip() or not self.routing_algorithm_version.strip():
            raise ValueError("cache and routing versions must be non-empty")
        if self.log_format not in {"console", "json"}:
            raise ValueError("LOG_FORMAT must be console or json")
        for network_value in self.trusted_proxy_networks_list:
            try:
                ip_network(network_value, strict=False)
            except ValueError as exc:
                raise ValueError("TRUSTED_PROXY_NETWORKS contains an invalid network") from exc
        if self.app_env.lower() in {"production", "staging"}:
            if not self.cors_origins_list or "*" in self.cors_origins_list:
                raise ValueError("production and staging require an explicit CORS allowlist")
            if self.app_release == "development":
                raise ValueError("production and staging require APP_RELEASE")
            if self.metrics_enabled and not self.metrics_bearer_token:
                raise ValueError(
                    "production and staging require METRICS_BEARER_TOKEN when metrics are enabled"
                )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Parsed, trimmed list of allowed CORS origins (empty entries dropped)."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def trusted_proxy_networks_list(self) -> list[str]:
        return [value.strip() for value in self.trusted_proxy_networks.split(",") if value.strip()]


settings = Settings()
