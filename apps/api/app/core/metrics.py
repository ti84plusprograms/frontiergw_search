"""Bounded Prometheus metrics used by the API and operations services."""

from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "endpoint"])
HTTP_RESPONSES = Counter("http_responses_total", "HTTP responses", ["endpoint", "status_class"])
HTTP_DURATION = Histogram(
    "http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"]
)
SEARCH_REQUESTS = Counter("search_requests_total", "Search requests", ["cache_outcome"])
SEARCH_DURATION = Histogram("search_duration_seconds", "Search duration", ["connections"])
SEARCH_RESULTS = Histogram("search_results_count", "Search result count", ["connections"])
SEARCH_NO_RESULTS = Counter("search_no_results_total", "Searches with no results")
AIRPORT_REQUESTS = Counter("airport_search_requests_total", "Airport search requests")
AIRPORT_DURATION = Histogram("airport_search_duration_seconds", "Airport search duration")
CACHE_HITS = Counter("cache_hits_total", "Cache hits", ["namespace"])
CACHE_MISSES = Counter("cache_misses_total", "Cache misses", ["namespace"])
CACHE_ERRORS = Counter("cache_errors_total", "Cache errors", ["operation"])
REDIS_FAILURES = Counter("redis_failures_total", "Redis failures", ["operation"])
REDIS_DURATION = Histogram(
    "redis_operation_duration_seconds", "Redis operation duration", ["operation"]
)
RATE_LIMITED = Counter("rate_limit_exceeded_total", "Rate limit responses", ["endpoint"])
SCHEDULE_IMPORTS = Counter("schedule_import_total", "Schedule imports", ["outcome"])
SCHEDULE_IMPORT_FAILURES = Counter("schedule_import_failures_total", "Failed schedule imports")
DATABASE_HEALTH = Gauge("database_health", "Database health, one for healthy")
DATABASE_QUERY_DURATION = Histogram(
    "database_query_duration_seconds", "Database query duration", ["operation"]
)
ACTIVE_SCHEDULE = Gauge("active_schedule_version", "Whether an active schedule exists")
APPLICATION_INFO = Gauge("application_info", "Application release info", ["environment", "release"])
