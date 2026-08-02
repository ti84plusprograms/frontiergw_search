# Performance Baseline

The repeatable synthetic workload is `make load-baseline` against the Docker staging stack. It uses 20 concurrent users for two minutes and covers airport lookup, cached and uncached direct/connecting searches, empty results, schedule status, and rate bursts. Redis-outage timing is measured by stopping only the ephemeral Redis container and rerunning the smoke workload.

Dataset: six synthetic airports, twelve scheduled flights, twelve routes, daily/selected weekday service from 2026-08-01 through 2026-12-31. ATL on 2026-08-04 is the primary direct/connecting query. No external provider is called.

Acceptance thresholds are airport p95 below 200 ms, cached search p95 below 250 ms, uncached direct p95 below 500 ms, uncached one-stop p95 below 1 second, unexpected server errors below 1%, and no more than 20% p95 regression from the last accepted baseline. The CI smoke uses two users for ten seconds and is a failure detector, not the release baseline.

## Local acceptance run — 2026-08-01

The complete two-minute baseline ran on the local Docker Desktop stack with 20 users and a spawn rate of four users per second. It completed 7,392 requests at 62.41 requests/second with zero failures. Aggregate p95 was 30 ms and p99 was 71 ms.

| Scenario | p95 | p99 |
| --- | ---: | ---: |
| Airport lookup | 13 ms | 38 ms |
| Schedule status | 12 ms | 44 ms |
| Cached direct search | 27 ms | 69 ms |
| No-result search | 25 ms | 74 ms |
| Rate burst | 27 ms | 64 ms |
| Uncached connecting search | 45 ms | 97 ms |
| Uncached direct search | 39 ms | 100 ms |

The highest observed request latency was 221 ms. At the end of the run, the API used 72.74 MiB, PostgreSQL 37.86 MiB, and Redis 13.83 MiB. These are observations from the local runner, not production capacity guarantees.

The primary route query used `idx_flights_origin_effective`, joined the active data source by primary key, returned three rows, planned in 1.398 ms, and executed in 0.388 ms. The workload produced no connection-pool errors.

Redis degradation was tested without restarting the API. Search continued successfully while Redis was stopped, readiness reported `degraded`, and the same running API resumed cache misses and hits after Redis returned and the bounded 30-second error backoff expired. PostgreSQL remained required for readiness.

All local latency and error thresholds passed. The initial run did not preserve a Prometheus counter snapshot suitable for an aggregate cache-hit ratio, and a single end-of-run memory snapshot does not prove longitudinal memory stability. Those two measurements remain required in the remote baseline. QA-002 remains `IN REVIEW` until that evidence and the repeatable GitHub Actions staging job pass on the remote runner; the 20% regression gate will use this run as the initial latency comparison baseline.
