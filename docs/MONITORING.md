# Monitoring and Alerts

The approved stack is structured JSON logs, Prometheus-compatible metrics, and optional Sentry error reporting. Configure `LOG_FORMAT=json` in staging/production. Logs are built from an allowlist; URLs, raw queries, headers, cookies, credentials, secrets, payment data, and passport data are dropped. Request IDs, releases, safe cache hashes, bounded route labels, status classes, and durations are allowed.

Set `MONITORING_ENABLED=true` and a server-only `SENTRY_DSN` to enable backend reporting. The frontend uses `NEXT_PUBLIC_SENTRY_DSN`. Both set environment/release tags and disable default PII, session replay, and trace sampling. Monitoring failures are caught and cannot fail requests. Do not put a secret-bearing DSN in source control.

`/metrics` is enabled by `METRICS_ENABLED`. Staging and production refuse to start with metrics enabled unless `METRICS_BEARER_TOKEN` is set; unauthorized requests receive a generic 404. Disable metrics when no private scrape path exists. Never expose the token to the frontend.

Initial adjustable alert thresholds:

- HTTP 5xx above 1% for five minutes: page the on-call engineer.
- Search p95 above 1 second for ten minutes: investigate database/cache latency.
- Database health at zero or readiness failure for two minutes: page immediately.
- No active schedule: page immediately and disable public search if results could be wrong.
- Redis failures sustained for ten minutes: warn; search remains available.
- Import failure, schedule expiry within seven days, or zero-result spike above 3x baseline: investigate during the current support window.
- Rate-limit responses above 10% for ten minutes or frontend errors above 2%: investigate abuse/configuration or a release regression.

Metrics use bounded labels only. Request IDs, cache keys, airports, user agents, exception text, and URLs are never metric labels.
