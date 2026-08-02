# Operations Runbook

## Start, migrate, and seed

```bash
docker compose -f infrastructure/docker-compose.yml up -d postgres redis
docker compose -f infrastructure/docker-compose.yml run --rm api alembic upgrade head
docker compose -f infrastructure/docker-compose.yml run --rm api python -m app.cli airport-seed data/fixtures/sample_airports.csv
docker compose -f infrastructure/docker-compose.yml run --rm api python -m app.cli schedule-import data/fixtures/sample_schedule.csv
docker compose -f infrastructure/docker-compose.yml up -d --wait api web
```

Check `/api/v1/health/live` for process liveness and `/api/v1/health/ready` for PostgreSQL plus active-schedule readiness. Redis outage returns `status=degraded` but HTTP 200. Use `/api/v1/schedules/status` and `APP_RELEASE` to identify data and code releases. Stop with `docker compose -f infrastructure/docker-compose.yml down`; volumes are retained.

## Diagnosis

- API logs: `docker compose -f infrastructure/docker-compose.yml logs -f api`.
- Metrics: authenticated `GET /metrics` when enabled.
- PostgreSQL failure: inspect Postgres logs, credentials, pool saturation, migration state, and `SELECT 1`; readiness must remain 503 until corrected.
- Redis failure: inspect Redis logs/network and `redis_failures_total`; verify search still returns correct results. Restarting the API is not required for normal recovery.
- Active data: `docker compose -f infrastructure/docker-compose.yml exec api python -m app.cli schedule-status`.
- Import only synthetic/approved provider files through the CLI. A failed import leaves the prior active dataset unchanged.

## Configuration and rollback

Change rate limits or TTLs through environment variables and restart the API. Disable cache with `CACHE_ENABLED=false`; disable public rate limiting with `RATE_LIMIT_ENABLED=false` only as a time-bounded incident action. Roll back frontend/backend to the previous image identified by `APP_RELEASE`, run only forward-safe migrations, and never automatically reverse a destructive migration. Restore a prior schedule by re-importing its exact approved source under a new source version; do not edit applied migrations or database rows manually. Verify liveness, readiness, airport lookup, direct search, one-stop search, and price/availability labels after rollback.
