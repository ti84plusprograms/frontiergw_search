# Caching and Redis Resilience

Phase 5 caches airport autocomplete, schedule status, successful searches, and empty searches behind `CacheService`. Redis is optional: every connection, read, write, invalidation, lock, and rate-limit failure falls back to uncached/unlimited execution after a bounded timeout and emits a log/metric.

Search keys are SHA-256 based and contain no raw criteria. Identity includes `CACHE_SCHEMA_VERSION`, `ROUTING_ALGORITHM_VERSION`, the active schedule source/version, canonical normalized criteria, `MAX_SEARCH_RESULTS`, and an exact pricing fingerprint. New schedule versions therefore bypass old entries. Successful imports also invalidate the bounded schedule-status namespace after the database transaction commits.

Cached search payloads exclude `search_id` and `generated_at`. Both are regenerated for every response. Empty results use `NO_RESULT_CACHE_TTL_SECONDS`; same-day results use the shorter same-day TTL. A short Redis lock bounds stampedes but never causes callers to wait; callers compute normally if the lock is held or Redis fails.

To bypass caching, set `CACHE_ENABLED=false` and restart the API. To force invalidation without scanning Redis, increment `CACHE_SCHEMA_VERSION`, `ROUTING_ALGORITHM_VERSION`, or the applicable pricing configuration. `FLUSHDB` is permitted only in an isolated development/test Redis database, never on a shared production instance.

Relevant metrics are `cache_hits_total`, `cache_misses_total`, `cache_errors_total`, `redis_failures_total`, and `redis_operation_duration_seconds`.
