# Active Phase

## Phase

Phase 5 — Reliability, Security, Caching, Observability, and Release Hardening

## Objective

Harden the completed search product so it can operate reliably under realistic development, staging, and early production workloads.

At the end of Phase 5, the system must:

* Cache eligible search and reference-data responses safely.
* Remain functional when Redis is unavailable.
* Apply bounded and configurable request-rate limits.
* Produce structured logs with request correlation.
* Collect useful application and search metrics.
* Report unexpected errors through the configured monitoring platform.
* Provide actionable health and readiness information.
* Enforce baseline web and API security controls.
* Run comprehensive end-to-end, accessibility, timezone, contract, and performance tests.
* Validate deployment artifacts and operational procedures.
* Support a controlled staging deployment.
* Provide a documented release and rollback process.

Phase 5 does not add live Frontier availability, Frontier authentication, browser automation, AI recommendations, user accounts, or payment functionality.

---

# Included Tasks

Only the following tasks are included in Phase 5:

* OPS-001 — Add caching
* OPS-002 — Add structured logging
* OPS-003 — Add rate limiting
* OPS-004 — Add monitoring and error reporting
* QA-001 — Add end-to-end tests
* QA-002 — Add routing and API performance tests
* QA-003 — Add timezone and edge-case validation suite

Phase 5 also includes the minimum security, deployment validation, and operational documentation required to complete those tasks.

No additional product feature is part of the active phase unless this file is explicitly amended and approved.

---

# Explicitly Excluded

The following functionality is not part of Phase 5:

* Live GoWild availability
* Exact Frontier taxes and fees
* Frontier account authentication
* Frontier credential storage
* Frontier browser automation
* Official Frontier NDC integration
* Third-party live flight shopping
* Flight booking
* Payment processing
* User accounts
* Saved searches
* Notifications
* Price alerts
* Natural-language search
* LLM-based destination ranking
* Weather integration
* Hotel or rental-car pricing
* Round-trip optimization
* Multi-city routing
* More than one connection
* Native mobile applications
* Production-scale multi-region deployment
* Automatic merging to the production branch
* Automatic production release without human approval

Partial implementation of an excluded feature must not be required by Phase 5 builds, tests, CI, staging deployment, or monitoring.

---

# Requirement Authority

Use this precedence when evaluating Phase 5 work:

1. `PHASE.md` defines the exact active scope and completion gate.
2. `DECISIONS.md` defines approved architectural decisions.
3. `docs/PRD.md` defines overall product requirements.
4. `docs/TDD.md` defines the overall technical design.
5. `TASKS.md` records task status and dependencies.

`TASKS.md` cannot expand the active phase.

An incorrectly completed future task must be corrected to its factual status. Do not implement an excluded feature merely to preserve an inaccurate task status.

Phase 5 must preserve all accepted behavior and contracts from Phases 1 through 4 unless a regression fix or accepted ADR requires a change.

---

# Core Design Rules

## Deterministic Pass/Fail Gates

Agents and reviewers must not determine completion based on subjective confidence.

Phase 5 completion depends on:

* Executable tests
* Reproducible commands
* Measured results
* Verified configuration
* Green remote CI
* Successful staging validation
* Documented exceptions through accepted ADRs

---

## Graceful Degradation

Optional infrastructure must not become a single point of failure.

In particular:

* Redis failure must not make schedule search unavailable.
* Monitoring-provider failure must not make the application unavailable.
* Analytics failure must not fail user requests.
* Metrics-export failure must not change search results.
* Log-export failure must not corrupt application behavior.

PostgreSQL remains a required dependency for schedule-backed search.

---

## Preserve Deterministic Search

Caching, rate limiting, logging, tracing, and monitoring must not change:

* Route validity
* Itinerary identity
* Timezone calculations
* Price estimates
* Filter behavior
* Sorting behavior
* Public API semantics

The same uncached search inputs against the same active schedule dataset must produce the same search result content as the corresponding cached response, excluding permitted request-specific metadata.

---

## Security by Default

Phase 5 must use restrictive, explicit configuration.

Avoid:

* Production wildcard CORS
* Unbounded request sizes
* Unbounded query limits
* Secrets in source control
* Secrets in client bundles
* Sensitive request logging
* Raw stack traces in API responses
* Unauthenticated administrative write endpoints
* Automatic destructive operations
* Broad service-account permissions

---

# Required Phase 5 Behavior

# OPS-001 — Caching

## 1. Cache Architecture

Redis is the preferred shared cache.

The cache layer must be isolated behind an application interface.

Recommended service boundary:

```text
services/
  cache_service.py

repositories/
  cached_schedule_repository.py

core/
  cache_keys.py
  cache_config.py
```

Exact file names may differ.

Application services must not depend directly on provider-specific Redis client behavior.

---

## 2. Cacheable Data

Phase 5 may cache:

* Airport autocomplete results
* Schedule-status responses
* Deterministic itinerary-search responses
* Active schedule-version metadata
* Negative or no-result search responses
* Generated OpenAPI-independent reference metadata where appropriate

Phase 5 must not cache:

* Raw secrets
* Authentication credentials
* Full request headers
* User-specific sensitive data
* Unvalidated requests
* Internal exception responses
* Mutable database sessions
* Live availability, because it is not yet implemented

---

## 3. Search Cache Key

The search-cache key must be based on normalized, result-defining inputs.

It must include at least:

* Cache schema version
* Routing algorithm version
* Active schedule-source identifier or version
* Origin
* Departure date
* Maximum connections
* Connection-duration limits
* Time filters
* Maximum total duration
* Maximum price
* Geography filters
* Sort mode
* Result-limit or pagination parameters
* Estimated-pricing configuration version

Recommended format:

```text
search:v1:{schedule_version}:{algorithm_version}:{criteria_hash}
```

The criteria hash must use canonical serialization.

The cache key must not depend on:

* Request ID
* Header order
* JSON field order
* User-agent string
* Frontend URL formatting
* Unrelated environment values

---

## 4. Cache Response Semantics

A cache hit must preserve the public search contract.

Request-specific fields may be regenerated, including:

* Request ID
* Response-generated timestamp, if its semantics are explicitly defined
* Cache-status metadata

The application must not incorrectly present an old generation timestamp as a fresh routing computation.

Recommended optional metadata:

```json
{
  "cache": {
    "status": "HIT",
    "stored_at": "2026-08-01T14:00:00Z",
    "age_seconds": 42
  }
}
```

If this metadata is added, it becomes part of the documented public contract and requires contract tests.

---

## 5. Cache TTLs

TTL values must be configurable.

Recommended initial defaults:

```text
AIRPORT_SEARCH_CACHE_TTL_SECONDS=21600
SCHEDULE_STATUS_CACHE_TTL_SECONDS=300
SEARCH_CACHE_TTL_SECONDS=1800
SAME_DAY_SEARCH_CACHE_TTL_SECONDS=300
NO_RESULT_CACHE_TTL_SECONDS=300
CACHE_ERROR_BACKOFF_SECONDS=30
```

These values may be changed through configuration or an accepted ADR.

Same-day and near-departure searches should generally use shorter TTLs than distant searches.

---

## 6. Cache Invalidation

Relevant search caches must be invalidated when:

* A new schedule version becomes active.
* Airport metadata changes materially.
* Routing algorithm version changes.
* Search response schema changes.
* Pricing-estimator configuration changes.
* A critical routing defect requires forced invalidation.

Acceptable invalidation strategies include:

* Versioned cache keys
* Namespace invalidation
* Explicit key deletion
* Short TTL plus version changes

Versioned keys are preferred over scanning and deleting all Redis keys.

---

## 7. Redis Failure Behavior

When Redis is unavailable:

* Airport search must query PostgreSQL directly.
* Schedule status must query PostgreSQL directly.
* Itinerary search must execute normally without cache.
* The request may be slower but must remain correct.
* The error must be logged and measured.
* The API must not return HTTP 500 solely because Redis is unavailable.
* Redis reconnection must not require an application restart where the selected client supports recovery.

A cache timeout must be bounded.

Recommended timeout:

```text
CACHE_OPERATION_TIMEOUT_MS=100
```

The exact value must be configurable.

---

## 8. Cache Stampede Protection

For frequently repeated searches, the system must avoid uncontrolled duplicate recomputation where practical.

Acceptable initial strategies:

* Short-lived distributed lock
* Single-flight request coalescing
* Probabilistic early refresh
* Small TTL jitter

A complex distributed-lock system is not mandatory if measured load does not justify it. The selected behavior must be documented.

The application must not hold a cache lock while waiting indefinitely.

---

## 9. Cache Tests

Required tests include:

* Cache miss executes routing.
* Cache hit avoids duplicate routing execution.
* Equivalent normalized requests share a cache key.
* Materially different requests do not share a cache key.
* Active schedule-version change invalidates prior results.
* Pricing-configuration change invalidates prior results.
* No-result responses are cached using the configured TTL.
* Redis timeout falls back to uncached execution.
* Redis connection failure falls back to uncached execution.
* Corrupt cache value is ignored and replaced.
* Cache response matches uncached response semantics.
* Request IDs are not reused incorrectly from cached data.
* Cache keys do not contain sensitive data.

---

# OPS-002 — Structured Logging

## 1. Log Format

Backend application logs must use a structured machine-readable format in staging and production.

Recommended format:

```json
{
  "timestamp": "2026-08-01T15:10:42.123Z",
  "level": "INFO",
  "event": "search.completed",
  "request_id": "req_123",
  "method": "POST",
  "path": "/api/v1/search",
  "status_code": 200,
  "duration_ms": 241,
  "origin": "ATL",
  "departure_date": "2026-08-04",
  "max_connections": 1,
  "result_count": 18,
  "cache_status": "HIT",
  "schedule_version": "2026-08-01"
}
```

Local development may use readable console formatting if the same structured fields remain available.

---

## 2. Required Request Fields

For each API request, logs must make it possible to identify:

* Request ID
* Method
* Path
* HTTP status
* Request duration
* Application environment
* Release or build version
* Error code, when applicable

Search requests should additionally include:

* Origin
* Departure date
* Maximum connections
* Result count
* Cache hit, miss, bypass, or error
* Active schedule version
* Routing duration
* Serialization duration where measured

Airport searches should include:

* Query length
* Result count
* Cache status

Do not log the full raw airport query when the project later permits sensitive free-form user text. In Phase 5, airport queries are low risk, but logging normalized bounded values is still preferable.

---

## 3. Required Operational Events

Structured events must exist for:

```text
application.started
application.stopped
database.connection_failed
redis.connection_failed
cache.hit
cache.miss
cache.error
search.started
search.completed
search.failed
airport_search.completed
rate_limit.exceeded
schedule_import.started
schedule_import.completed
schedule_import.failed
health.degraded
unexpected_error
```

Equivalent stable event names may be used.

---

## 4. Sensitive Data Redaction

Logs must not include:

* Database URLs
* Redis URLs
* API keys
* Authorization headers
* Cookies
* Session identifiers intended to be secret
* Full environment dumps
* Raw stack traces in normal informational logs
* Frontier credentials
* Payment information
* Passport information
* Complete inbound headers
* Secret-bearing query parameters

Redaction must be centralized where practical.

---

## 5. Request ID

The API must:

* Accept a valid inbound request ID where policy permits, or generate one.
* Prevent excessively long or malformed inbound IDs.
* Return the request ID in the response.
* Include it in all request-scoped logs.
* Include it in API error responses.
* Include it in monitoring events.

Recommended response header:

```text
X-Request-ID
```

---

## 6. Correlation

Where background or nested operations occur, logs should include:

* Request ID
* Search ID
* Import ID
* Cache key hash or safe cache identifier
* Schedule source version

Do not log full cache keys when they contain user criteria unless the format is confirmed safe.

---

## 7. Logging Failure Behavior

Failure to emit a log must not fail a user request.

Logging handlers must avoid uncontrolled blocking.

A remote log destination must not be called synchronously on the critical request path unless bounded and justified.

---

## 8. Logging Tests

Required tests include:

* Request ID generated when absent.
* Valid request ID propagated when supplied.
* Invalid or oversized request ID replaced.
* Request ID appears in error responses.
* Structured search completion event contains required fields.
* Cache events contain cache status.
* Sensitive configuration values are redacted.
* Authorization and cookie headers are not logged.
* Logging failure does not fail the search.
* Unexpected exceptions produce one correlated error event.

---

# OPS-003 — Rate Limiting

## 1. Rate-Limit Scope

Phase 5 must rate-limit at least:

* Airport search endpoint
* Itinerary search endpoint
* Any expensive administrative read endpoint
* Schedule import or activation endpoint, if publicly reachable
* Health endpoint only if needed to prevent abuse without breaking platform probes

Recommended initial anonymous limits:

```text
Airport search:
120 requests per minute per client

Itinerary search:
30 requests per minute per client

Schedule status:
60 requests per minute per client
```

Exact values must be configurable.

---

## 2. Client Identification

Before authentication exists, the limiter may identify clients using:

* Trusted reverse-proxy client IP
* Direct client IP
* A bounded anonymous session identifier
* A documented combination

The system must not blindly trust arbitrary forwarded headers.

Trusted proxy behavior must be configurable and documented.

---

## 3. Rate-Limit Response

Exceeded limits must return:

```http
HTTP 429 Too Many Requests
```

The response must use the standard API error schema.

Recommended error code:

```text
RATE_LIMITED
```

Recommended headers:

```text
Retry-After
X-RateLimit-Limit
X-RateLimit-Remaining
X-RateLimit-Reset
```

Header naming may follow the selected library or standard, but behavior must be documented and tested.

---

## 4. Redis Failure Behavior

The rate limiter must define behavior when Redis is unavailable.

Choose and document one of:

### Fail open

Requests continue without distributed rate limiting.

Recommended for public read-only search during early operation.

### Local fallback

Apply an in-memory per-instance limiter.

Acceptable but not globally consistent.

### Fail closed

Reject requests.

Not recommended for Phase 5 public search.

Recommended Phase 5 policy:

```text
Fail open with an operational warning and metric.
```

A stricter policy may be used for administrative write endpoints.

---

## 5. Rate-Limit Granularity

Limits should distinguish endpoint cost.

Airport autocomplete should not share the same low threshold as itinerary search.

The limiter must avoid treating ordinary browser autocomplete as abuse.

A burst allowance may be configured.

---

## 6. Internal and Health Traffic

Platform health probes and approved internal monitoring may bypass normal public limits through a documented trusted mechanism.

Bypasses must not rely on a publicly forgeable header.

---

## 7. Rate-Limit Tests

Required tests include:

* Requests below limit succeed.
* Request above limit returns HTTP 429.
* `Retry-After` is present.
* Standard error schema is preserved.
* Airport and itinerary endpoints use separate limits.
* Limits reset after the configured interval.
* Invalid forwarded headers are not trusted.
* Redis failure follows documented fallback.
* Rate-limit event is logged and measured.
* Health probes remain functional.
* Concurrent requests do not exceed the accepted tolerance of the chosen algorithm.

---

# OPS-004 — Monitoring and Error Reporting

## 1. Error Monitoring

The application must integrate with an approved monitoring platform such as Sentry or an equivalent.

The integration must support:

* Backend unexpected exceptions
* Frontend runtime errors
* Failed API requests where appropriate
* Release-version tagging
* Environment tagging
* Request-ID correlation
* Source-map support for frontend builds
* Sensitive-data filtering

The application must remain functional when the monitoring service is unavailable.

---

## 2. Captured Errors

Capture:

* Unhandled backend exceptions
* Unhandled frontend exceptions
* Failed schedule imports
* Database connectivity failures
* Repeated Redis failures
* Unexpected routing invariant failures
* Repeated HTTP 500 responses
* Deployment startup failures
* Critical background-job failures

Do not automatically report every expected validation error.

Expected HTTP 4xx responses should generally be measured but not sent as exception events.

---

## 3. Metrics

Required application metrics include:

```text
http_requests_total
http_request_duration_seconds
http_responses_total
search_requests_total
search_duration_seconds
search_results_count
search_no_results_total
airport_search_requests_total
airport_search_duration_seconds
cache_hits_total
cache_misses_total
cache_errors_total
rate_limit_exceeded_total
database_query_duration_seconds
redis_operation_duration_seconds
schedule_import_total
schedule_import_failures_total
active_schedule_version
application_info
```

Equivalent names may be used consistently.

---

## 4. Metric Labels

Labels must remain bounded.

Acceptable labels include:

* Endpoint
* HTTP method
* Status class
* Cache outcome
* Search connection count
* Environment
* Failure category

Avoid unbounded labels such as:

* Request ID
* Search ID
* Full URL
* Airport query string
* Arbitrary exception message
* User agent
* Cache key
* Stack trace

Airport codes may be omitted as labels to avoid high cardinality as the network expands.

---

## 5. Metrics Endpoint

The backend may expose:

```text
/metrics
```

when using Prometheus-compatible collection.

Requirements:

* It must not expose secrets.
* Public exposure must be controlled.
* Production access should be restricted to approved monitoring infrastructure.
* It must remain outside normal API response schemas.
* It must not require the frontend.

An alternative managed metrics exporter is acceptable.

---

## 6. Health and Readiness

Phase 5 must distinguish:

### Liveness

The process is running.

Recommended endpoint:

```text
/health/live
```

### Readiness

The application can serve core traffic.

Recommended endpoint:

```text
/health/ready
```

### Detailed diagnostic health

Optional protected endpoint:

```text
/api/v1/health
```

Readiness should evaluate at least:

* Application initialization
* PostgreSQL connectivity
* Required database schema or migration state
* Active schedule availability

Redis should generally be treated as a degradable dependency, not a readiness blocker, because search must work without it.

Recommended readiness behavior:

```text
PostgreSQL unavailable → not ready
No active schedule → not ready for search
Redis unavailable → ready but degraded
Monitoring unavailable → ready but degraded
```

---

## 7. Operational Alerts

Configure or document alerts for:

* HTTP 500 rate above threshold
* Search p95 latency above threshold
* Database connectivity failure
* No active schedule
* Schedule data nearing expiration
* Schedule import failure
* Sustained Redis failure
* Rate-limit spikes
* Zero-result spike across major test origins
* Frontend runtime error spike
* Deployment startup failure

Thresholds must be documented and adjustable.

---

## 8. Monitoring Tests

Required tests or controlled validation include:

* Backend unexpected exception is captured.
* Frontend test exception is captured in staging or a mocked integration.
* Sensitive headers are excluded.
* Request ID is attached to error event.
* Release and environment tags are present.
* Monitoring outage does not fail application requests.
* Metrics endpoint or exporter produces expected metric names.
* Metric labels remain bounded.
* Readiness fails when PostgreSQL is unavailable.
* Readiness reports degraded rather than failed when Redis is unavailable.
* No-active-schedule readiness behavior matches policy.

---

# Security Hardening

## 1. Security Headers

The frontend and API must use appropriate headers where applicable:

```text
Content-Security-Policy
X-Content-Type-Options
Referrer-Policy
Permissions-Policy
Strict-Transport-Security
```

`Strict-Transport-Security` must be enabled only in environments served exclusively through HTTPS.

Framing protection must be included through CSP `frame-ancestors` or an equivalent header.

The CSP must not be weakened to unrestricted values merely to suppress errors.

---

## 2. CORS

CORS must:

* Use an explicit allowlist.
* Support local development origins through configuration.
* Avoid `*` in production.
* Avoid allowing credentials unless required.
* Reject unauthorized origins.
* Document preview-deployment behavior.

---

## 3. Request Bounds

The API must enforce limits for:

* Request body size
* Airport result count
* Search result count
* Connection range
* Search date range
* String lengths
* Request-ID length
* URL parameter length where supported by infrastructure

Requests exceeding bounds must fail using the standard error contract.

---

## 4. Administrative Surfaces

Any administrative endpoint capable of:

* Triggering schedule import
* Activating a dataset
* Clearing caches
* Viewing detailed diagnostics
* Modifying configuration

must not be publicly writable without authentication or an equivalent trusted control.

If administrative writes are not needed in Phase 5, they should remain CLI-only or disabled.

---

## 5. Secrets

Secrets must:

* Be provided through environment or secret-management integration.
* Be absent from source control.
* Be absent from frontend bundles.
* Be absent from `.env.example` values.
* Be redacted from logs and monitoring.
* Be rotated when accidentally exposed.

Required secret scanning must run in CI.

---

## 6. Dependency Security

CI must include:

* Python dependency audit
* Node dependency audit
* Secret scanning
* Static analysis where practical
* Container-image vulnerability scan where container deployment is supported

Policy for findings:

* Critical vulnerabilities block release unless an accepted exception exists.
* High vulnerabilities block release when exploitable in the deployed path.
* Moderate and low findings must be documented and triaged.
* Audits must not silently ignore failed execution.

A documented allowlist may be used for verified false positives.

---

## 7. Security Tests

Required tests or validation include:

* Production CORS wildcard is absent.
* Unauthorized origin is rejected.
* Security headers are present.
* Request-body limit is enforced.
* Oversized request ID is rejected or replaced.
* API error does not leak stack traces.
* API error does not leak database details.
* Secrets are absent from frontend build output.
* Secret scan passes.
* Dependency audits execute successfully.
* Administrative write surfaces are protected or absent.
* Metrics endpoint exposure follows policy.

---

# QA-001 — End-to-End Test Suite

## 1. E2E Environment

End-to-end tests must run against:

* A real frontend build or representative test server
* A real FastAPI application
* PostgreSQL
* Redis where cache behavior is being tested
* Synthetic airport and schedule fixtures
* Stable test configuration

E2E tests must not call Frontier or any external live flight provider.

---

## 2. Required E2E Scenarios

The suite must include at least:

1. Load the search page.
2. Search for an airport by exact code.
3. Search for an airport by city.
4. Select an airport using the keyboard.
5. Select a supported departure date.
6. Submit a direct-only search.
7. View a direct itinerary.
8. Enable one-stop search.
9. View a one-stop itinerary.
10. Apply a maximum estimated-price filter.
11. Apply a departure-time filter.
12. Apply domestic-only filtering.
13. Change sorting.
14. Refresh and preserve URL state.
15. Open a copied or shared results URL.
16. Navigate Back and Forward.
17. Display no-results state.
18. Display validation error.
19. Display API server error.
20. Retry a failed search.
21. Display data-freshness information.
22. Display estimated-price disclaimer.
23. Display availability-not-checked status.
24. Use the primary flow at a mobile viewport.
25. Complete the primary flow using keyboard-only navigation.
26. Exercise a cached repeated search.
27. Verify search still works when Redis is unavailable.
28. Verify rate-limit response behavior in a controlled test.
29. Verify request ID appears in unexpected-error diagnostics.
30. Verify no external Frontier request occurs.

---

## 3. E2E Stability

Tests must avoid:

* Arbitrary sleep delays
* Dependence on wall-clock current date without explicit fixture control
* Dependence on external networks
* Shared mutable test data without reset
* Order dependence
* Random fixture assumptions
* Brittle selectors based only on styling classes

Use stable semantic selectors and explicit readiness conditions.

---

## 4. E2E Artifacts

On failure, CI should preserve:

* Screenshot
* Browser trace
* Relevant frontend logs
* Relevant API logs
* Test report
* Request ID when available

Video recording is optional.

Artifacts must not expose secrets.

---

# QA-002 — Performance and Load Validation

## 1. Performance Test Scope

Performance testing must cover:

* Airport search
* Direct itinerary search
* Direct plus one-stop search
* Cached search
* Uncached search
* No-result search
* Schedule-status endpoint
* Rate limiter under burst traffic
* Redis failure fallback
* PostgreSQL connection-pool behavior

---

## 2. Test Dataset

Performance tests must document:

* Airport count
* Route count
* Scheduled-flight count
* Active date range
* Number of first-segment candidates
* Number of second-segment candidates
* Expected result count

Synthetic data may be scaled to approximate realistic search complexity.

---

## 3. Initial Performance Targets

Unless superseded by an accepted ADR:

### Airport search

```text
p50 < 75 ms
p95 < 200 ms
p99 < 400 ms
```

### Cached itinerary search

```text
p50 < 100 ms
p95 < 250 ms
p99 < 500 ms
```

### Uncached direct search

```text
p50 < 250 ms
p95 < 500 ms
p99 < 900 ms
```

### Uncached direct plus one-stop search

```text
p50 < 500 ms
p95 < 1 second
p99 < 2 seconds
```

These targets apply to the documented staging or local benchmark environment and dataset.

---

## 4. Concurrency Target

The staging system must support at least:

```text
20 concurrent search users
```

without:

* Request corruption
* Incorrect mixed results
* Database pool exhaustion
* Unbounded memory growth
* Sustained error rates above the accepted threshold

Recommended initial error-rate target:

```text
Less than 1% unexpected server errors
```

Expected HTTP 4xx responses generated intentionally by the load test must be excluded from the server-error rate.

---

## 5. Cache Performance

The performance report must show:

* Cache hit ratio under repeated workload
* Cached versus uncached latency
* Redis-operation latency
* Behavior during Redis outage
* Recovery after Redis restoration
* Whether cache stampede occurs during concurrent misses

---

## 6. Database Performance

The performance review must identify:

* Slow queries
* Missing indexes
* N+1 query patterns
* Connection-pool exhaustion
* Lock contention
* Excessive repeated airport lookups
* Full-table scans on expected search paths

Query-plan inspection is required for the primary schedule queries.

---

## 7. Performance Regression Gate

CI may use a lightweight benchmark threshold.

Full load testing may run:

* On demand
* Nightly
* Before release
* In staging

A regression above an agreed tolerance must block release or receive an accepted exception.

Recommended regression tolerance:

```text
No more than 20% p95 degradation against the recorded baseline
```

---

# QA-003 — Timezone and Edge-Case Validation

## 1. Required Timezone Cases

The validation suite must include:

* Same-timezone flight
* Eastbound timezone change
* Westbound timezone change
* Cross-midnight arrival
* Cross-midnight connection
* Spring-forward transition
* Fall-back transition
* DST-observing origin to non-DST destination
* Non-DST origin to DST-observing destination
* Ambiguous local time
* Nonexistent local time
* Arrival-day offset zero
* Arrival-day offset one
* Connection exactly at minimum
* Connection exactly at maximum
* Connection one minute below minimum
* Connection one minute above maximum

---

## 2. Required Routing Edge Cases

Include:

* No active schedule
* Date at schedule effective start
* Date at schedule effective end
* Date outside coverage
* Inactive airport
* Inactive schedule source
* Duplicate scheduled flights
* Conflicting duplicate schedules
* Return-to-origin route
* Repeated connection airport
* Identical flight number on different routes
* Identical flight number on different dates
* Empty result set
* Maximum result truncation
* Stable tie sorting
* Zero-price misconfiguration
* Invalid currency configuration
* International estimate disabled
* Redis failure
* Database failure
* Corrupt cached response
* Rate-limit boundary
* Oversized request
* Invalid URL state
* Backend timeout
* Stale generated API types

---

## 3. Date and Clock Control

Tests must not depend on the uncontrolled current clock.

Use:

* Injected clock service
* Fixed timestamps
* Frozen time in tests
* Explicit fixture dates

Any code using the current time directly must be isolated behind a testable interface where current time affects behavior.

---

## 4. Cross-Layer Timezone Contract

Tests must verify consistency between:

* Database schedule definition
* Domain flight instance
* Routing itinerary
* API serialization
* Frontend rendering

The frontend must display the backend-provided local timestamps without introducing browser-timezone shifts.

---

# Frontend Reliability

## 1. Error Boundary

The frontend must include an error boundary or equivalent framework behavior for unexpected rendering failures.

It must:

* Show a usable fallback.
* Provide a retry or reload action.
* Include a safe request or event identifier where available.
* Report the error through monitoring.
* Avoid displaying raw stack traces.

---

## 2. API Failure Handling

The frontend must distinguish:

* Validation error
* Rate-limit error
* Network error
* Timeout
* Server error
* No-result success
* Stale or degraded data warning

A rate-limit error should tell the user when retry may succeed where `Retry-After` is available.

---

## 3. Request Cancellation

The frontend must avoid stale response replacement.

Autocomplete and search requests should:

* Be cancelled when superseded where supported, or
* Be ignored when their request sequence is stale.

---

## 4. Client Monitoring

Frontend monitoring must capture:

* Unhandled runtime errors
* Failed route rendering
* Repeated failed API requests
* Release version
* Environment
* Browser metadata within privacy policy
* Request ID when available

Session replay is not required and should not be enabled without a privacy review.

---

# Deployment Validation

## 1. Deployment Artifacts

Phase 5 must validate:

* Frontend production build
* Backend production image or package
* Database migration command
* Environment configuration validation
* Health and readiness checks
* Static asset serving
* Frontend source maps where monitoring requires them
* Container startup as a non-root user where practical

---

## 2. Staging Environment

A staging environment must be documented and should include:

* Frontend
* Backend
* PostgreSQL
* Redis
* Synthetic schedule data
* Monitoring
* Metrics
* HTTPS
* Explicit CORS configuration
* Release identifier

Staging must not use real Frontier credentials or automated Frontier access.

---

## 3. Migration Safety

Deployment validation must prove:

* Migrations run before or during deployment in a controlled manner.
* A failed migration prevents rollout.
* Existing data is preserved.
* The application does not start against an incompatible schema.
* Rollback procedure is documented.
* Previously applied migrations are not edited.

---

## 4. Rollback

The runbook must define:

* How to identify the deployed release
* How to roll back frontend
* How to roll back backend
* How to handle nonreversible migrations
* How to disable caching
* How to disable rate limiting if misconfigured
* How to restore the previous active schedule version
* How to verify service after rollback

Automatic destructive database rollback is not required.

---

## 5. Deployment Approval

Phase 5 may support staging deployment automatically.

Production deployment must still require explicit human approval.

---

# Operational Documentation

Required documentation includes:

```text
docs/RUNBOOK.md
docs/RELEASE_CHECKLIST.md
docs/INCIDENT_RESPONSE.md
docs/PERFORMANCE_BASELINE.md
docs/CACHING.md
docs/MONITORING.md
```

Equivalent organization is acceptable.

---

## Runbook Requirements

The runbook must cover:

* Starting and stopping services
* Checking health and readiness
* Running migrations
* Importing schedule data
* Checking the active schedule version
* Inspecting logs
* Inspecting metrics
* Diagnosing Redis failure
* Diagnosing PostgreSQL failure
* Clearing or bypassing cache safely
* Changing rate-limit configuration
* Confirming release version
* Rolling back a release
* Restoring the previous active schedule dataset

---

## Incident Response Requirements

Document severity levels and response steps for:

* Complete outage
* Elevated server errors
* Search latency degradation
* Incorrect route results
* Incorrect timezone display
* Incorrect estimated pricing
* No active schedule
* Expired schedule data
* Redis outage
* Database outage
* Security or secret exposure
* Monitoring outage

The document must state that incorrect route, time, or price behavior may require disabling search until corrected.

---

# CI/CD Requirements

## Pull Request Checks

Required checks include:

### Frontend

* Formatting
* Lint
* Type checking
* Unit/component tests
* Production build
* Accessibility smoke tests
* Generated API type check

### Backend

* Formatting
* Lint
* Type checking
* Unit tests
* Integration tests
* Routing and timezone tests
* Migration validation
* OpenAPI generation
* Cache and rate-limit tests

### Security

* Secret scan
* Python dependency audit
* Node dependency audit
* Static analysis
* Container scan where applicable

### Contract

* OpenAPI diff or contract check
* Generated frontend types are current
* Public enum stability

---

## Nightly or Release Checks

Recommended:

* Full E2E suite
* Full load test
* Dependency scans
* Container scan
* Schedule expiration check
* Migration from a clean database
* Migration from a Phase 4 database snapshot
* Redis-outage test
* Browser matrix test

---

## CI Reliability

CI must:

* Use locked dependencies.
* Fail when a required command is missing.
* Avoid relying on a developer’s local files.
* Start required services explicitly.
* Preserve useful failure artifacts.
* Avoid silently skipping failed test discovery.
* Avoid treating zero collected tests as success where tests are required.
* Use timeouts to prevent hung jobs.

---

# Configuration Requirements

Phase 5 must define and validate configuration equivalent to:

```text
APP_ENV
APP_RELEASE
DATABASE_URL
REDIS_URL
FRONTEND_URL
CORS_ALLOWED_ORIGINS

CACHE_ENABLED
AIRPORT_SEARCH_CACHE_TTL_SECONDS
SCHEDULE_STATUS_CACHE_TTL_SECONDS
SEARCH_CACHE_TTL_SECONDS
SAME_DAY_SEARCH_CACHE_TTL_SECONDS
NO_RESULT_CACHE_TTL_SECONDS
CACHE_OPERATION_TIMEOUT_MS

RATE_LIMIT_ENABLED
AIRPORT_RATE_LIMIT_PER_MINUTE
SEARCH_RATE_LIMIT_PER_MINUTE
SCHEDULE_STATUS_RATE_LIMIT_PER_MINUTE
TRUSTED_PROXY_COUNT

MONITORING_ENABLED
SENTRY_DSN
METRICS_ENABLED
LOG_LEVEL
LOG_FORMAT

REQUEST_BODY_MAX_BYTES
REQUEST_ID_MAX_LENGTH
MAX_SEARCH_RESULTS
```

Requirements:

* Invalid configuration must fail clearly.
* Secrets must not appear in validation errors.
* Test configuration must be explicit.
* Production configuration must not silently use insecure development defaults.
* Required production values must be enforced.

---

# Required Verification Commands

The exact commands must be updated to match the repository.

At minimum, Phase 5 must provide working commands equivalent to:

```bash
# Install
pnpm install --frozen-lockfile
cd apps/api && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.lock && pip install -e . --no-deps
cd ../..

# Infrastructure
docker compose -f infrastructure/docker-compose.yml config --quiet
docker compose -f infrastructure/docker-compose.yml up -d --wait postgres redis
docker compose -f infrastructure/docker-compose.yml run --rm api alembic upgrade head
docker compose -f infrastructure/docker-compose.yml run --rm api python -m app.cli airport-seed data/fixtures/sample_airports.csv
docker compose -f infrastructure/docker-compose.yml run --rm api python -m app.cli schedule-import data/fixtures/sample_schedule.csv
docker compose -f infrastructure/docker-compose.yml up -d --wait api web

# Static verification
make format-check
make lint
make typecheck

# Backend tests
cd apps/api && source .venv/bin/activate && pytest tests/ -v
DATABASE_URL_TEST=postgresql+psycopg://gowild:gowild@localhost:5432/gowild pytest tests/test_routing_integration.py tests/test_api_search_integration.py -v
pytest tests/test_api_caching.py tests/test_cache_and_rate_limit.py -v
pytest tests/test_operations_api.py -v
pytest tests/test_observability.py -v
pytest tests/test_flight_instance.py tests/test_routing_domain.py tests/test_routing_engine_regressions.py tests/test_routing_properties.py -v
cd ../..

# Frontend tests
pnpm --dir apps/web test
pnpm --dir apps/web type-check
pnpm --dir apps/web lint
pnpm --dir apps/web build

# Contract and security
make openapi && git diff --exit-code apps/api/openapi.json
pnpm --dir apps/web check:types
trufflehog filesystem . --results=verified,unknown
cd apps/api && pip-audit -r requirements.lock --no-deps --disable-pip && bandit -q -r app && cd ../..
pnpm audit --audit-level high
docker build -t gowild-api:phase5 apps/api && trivy image --exit-code 1 --severity CRITICAL,HIGH gowild-api:phase5
docker build -t gowild-web:phase5 -f apps/web/Dockerfile . && trivy image --exit-code 1 --severity CRITICAL,HIGH gowild-web:phase5

# End-to-end
pnpm --dir apps/web test:e2e
pnpm --dir apps/web test:e2e:fullstack

# Accessibility
pnpm --dir apps/web test:e2e --grep accessibility

# Performance
make load-smoke
make load-baseline

# Failure-mode validation
docker compose -f infrastructure/docker-compose.yml stop redis
curl --fail-with-body -H 'Content-Type: application/json' -d '{"origin":"ATL","departure_date":"2026-08-04","max_connections":0}' http://localhost:8000/api/v1/search
curl --fail-with-body http://localhost:8000/api/v1/health/ready
docker compose -f infrastructure/docker-compose.yml start redis
cd apps/api && source .venv/bin/activate && pytest tests/test_operations_api.py -k 'readiness or rate_limit' -v && cd ../..

# CI parity
make format-check lint typecheck test-ops
pnpm --dir apps/web check:types && pnpm --dir apps/web test && pnpm --dir apps/web build
docker compose -f infrastructure/docker-compose.yml config --quiet
```

No placeholder may remain in this section when Phase 5 is marked complete.

No agent may claim a command passed unless it was actually executed successfully.

---

# Task Status Rules

At the start of Phase 5:

* `FND-001` through `FND-008` remain `COMPLETE`.
* `DAT-001` through `DAT-006` remain `COMPLETE`.
* `RTE-001` through `RTE-007` remain `COMPLETE`.
* `API-001` through `API-003` remain `COMPLETE`.
* `WEB-001` through `WEB-004` remain `COMPLETE`.
* `OPS-001` through `OPS-004` begin as `NOT STARTED`.
* `QA-001` through `QA-003` begin as `NOT STARTED`.
* Availability, AI, user-account, and future product tasks remain `NOT STARTED`.

A Phase 5 task may be marked `COMPLETE` only when:

* Implementation exists.
* Required automated tests pass.
* Failure behavior is tested.
* Operational documentation is updated.
* Relevant staging validation succeeds.
* Remote CI passes.

Configuration alone does not complete an OPS task.

A test file that is skipped or not invoked by CI does not complete a QA task.

A monitoring integration that has not been validated does not complete OPS-004.

---

# Allowed Change Areas

Phase 5 may modify:

```text
apps/api/**
apps/web/**
packages/**
docs/**
data/**
infrastructure/**
.github/workflows/**
orchestration/**
TASKS.md
DECISIONS.md
PHASE.md
CLAUDE.md
AGENTS.md
README.md
Makefile
docker-compose.yml
pyproject.toml
package.json
pnpm-workspace.yaml
lockfiles
deployment configuration
monitoring configuration
```

Changes to routing, pricing, schedule ingestion, or public API semantics require:

* A reproducible defect
* A regression test
* Confirmation that prior phase contracts remain satisfied
* An ADR when documented behavior or architecture changes

---

# Change-Control Rules

Human approval is required before:

* Modifying the PRD
* Modifying the TDD’s core architecture
* Changing public API paths
* Removing public response fields
* Changing money serialization
* Changing timezone semantics
* Changing routing rules
* Changing cache consistency guarantees
* Changing Redis failure policy
* Changing rate-limit failure policy
* Adding a new monitoring vendor
* Adding a paid external service
* Exposing administrative write endpoints
* Adding authentication
* Adding live Frontier integration
* Adding browser automation
* Adding an LLM dependency
* Changing the active-phase task list
* Deploying to production
* Automatically merging to the protected main branch

Approved deviations must be recorded in `DECISIONS.md`.

---

# Phase 5 Completion Gate

Phase 5 is complete only when all applicable items below are satisfied.

## Scope

* [ ] Only OPS-001 through OPS-004 and QA-001 through QA-003 are evaluated as Phase 5 deliverables.
* [ ] No live Frontier provider has been added.
* [ ] No Frontier browser automation has been added.
* [ ] No user accounts or payment functionality has been added.
* [ ] No LLM is used for routing, pricing, or availability.
* [ ] Future-phase tasks remain factually marked.

## Caching

* [ ] Cache abstraction exists.
* [ ] Airport search caching works.
* [ ] Schedule-status caching works.
* [ ] Itinerary-search caching works.
* [ ] Cache keys use canonical normalized inputs.
* [ ] Active schedule version is part of cache identity.
* [ ] Routing or response version is part of cache identity.
* [ ] TTLs are configurable.
* [ ] No-result caching works.
* [ ] Corrupt cache entries are ignored safely.
* [ ] Redis timeout falls back to uncached search.
* [ ] Redis outage does not make search unavailable.
* [ ] Schedule activation invalidates or bypasses old cache entries.
* [ ] Cache behavior is tested.

## Logging

* [ ] Logs are structured in staging and production.
* [ ] Every request has a request ID.
* [ ] Request ID appears in response headers.
* [ ] Request ID appears in API errors.
* [ ] Search-completion logs contain required fields.
* [ ] Cache outcomes are logged.
* [ ] Rate-limit events are logged.
* [ ] Sensitive headers are not logged.
* [ ] Secrets are redacted.
* [ ] Logging failure does not fail user requests.
* [ ] Logging behavior is tested.

## Rate Limiting

* [ ] Airport search has a configured rate limit.
* [ ] Itinerary search has a configured rate limit.
* [ ] Schedule status has a configured rate limit.
* [ ] HTTP 429 uses the standard error schema.
* [ ] `Retry-After` or equivalent reset information is present.
* [ ] Client identification is documented.
* [ ] Untrusted proxy headers are not blindly accepted.
* [ ] Redis failure follows the documented policy.
* [ ] Health probes remain usable.
* [ ] Rate-limit behavior is tested.

## Monitoring and Metrics

* [ ] Backend unexpected exceptions are captured.
* [ ] Frontend unexpected exceptions are captured.
* [ ] Release and environment tags are present.
* [ ] Request IDs are attached to error events.
* [ ] Sensitive data is filtered.
* [ ] Monitoring outage does not fail user traffic.
* [ ] Required metrics exist.
* [ ] Metric labels are bounded.
* [ ] Search latency is measured.
* [ ] Cache hit and error metrics exist.
* [ ] Rate-limit metrics exist.
* [ ] Schedule-import failure metrics exist.
* [ ] Monitoring behavior is validated.

## Health and Readiness

* [ ] Liveness endpoint works.
* [ ] Readiness endpoint works.
* [ ] PostgreSQL failure makes readiness fail.
* [ ] No active schedule makes search readiness fail.
* [ ] Redis outage reports degraded state without failing readiness.
* [ ] Health responses do not expose secrets.
* [ ] Platform probes are documented.

## Security

* [ ] Production CORS uses an explicit allowlist.
* [ ] Security headers are present.
* [ ] CSP is valid and documented.
* [ ] Request-size limits are enforced.
* [ ] Search and airport limits are bounded.
* [ ] Secrets are absent from source control.
* [ ] Secrets are absent from frontend bundles.
* [ ] Secret scanning passes.
* [ ] Dependency audits execute successfully.
* [ ] Critical vulnerabilities are resolved or have accepted exceptions.
* [ ] Administrative write surfaces are protected or absent.
* [ ] API errors do not expose internal details.

## End-to-End Testing

* [ ] Core direct-search workflow passes.
* [ ] Core one-stop workflow passes.
* [ ] Filter and sorting workflows pass.
* [ ] URL persistence workflow passes.
* [ ] No-result workflow passes.
* [ ] Validation-error workflow passes.
* [ ] Server-error and retry workflow pass.
* [ ] Mobile workflow passes.
* [ ] Keyboard-only workflow passes.
* [ ] Cached search workflow passes.
* [ ] Redis-outage search workflow passes.
* [ ] No E2E test calls Frontier.
* [ ] Failure artifacts are preserved in CI.

## Timezone and Edge Cases

* [ ] Same-timezone case passes.
* [ ] Eastbound case passes.
* [ ] Westbound case passes.
* [ ] Cross-midnight arrival passes.
* [ ] Cross-midnight connection passes.
* [ ] Spring-forward case passes.
* [ ] Fall-back case passes.
* [ ] Ambiguous-time policy is tested.
* [ ] Nonexistent-time policy is tested.
* [ ] Minimum connection boundary passes.
* [ ] Maximum connection boundary passes.
* [ ] Duplicate schedule case passes.
* [ ] Return-to-origin exclusion passes.
* [ ] Frontend rendering preserves API timezone values.
* [ ] Tests use a controlled clock.

## Performance

* [ ] Airport-search benchmark is recorded.
* [ ] Cached-search benchmark is recorded.
* [ ] Uncached direct-search benchmark is recorded.
* [ ] Uncached one-stop benchmark is recorded.
* [ ] Twenty-concurrent-user load test completes.
* [ ] Unexpected server-error rate remains below threshold.
* [ ] Cache hit ratio is measured.
* [ ] Redis-outage behavior is measured.
* [ ] Primary query plans are inspected.
* [ ] No uncontrolled N+1 query pattern exists.
* [ ] No uncontrolled memory growth is observed.
* [ ] Performance baseline is documented.
* [ ] Material regressions have accepted exceptions or are fixed.

## CI/CD

* [ ] Pull-request CI runs all required static checks.
* [ ] Backend tests run.
* [ ] Frontend tests run.
* [ ] Contract tests run.
* [ ] Security scans run.
* [ ] E2E tests run in the selected release workflow.
* [ ] CI fails when expected test discovery is missing.
* [ ] CI preserves failure artifacts.
* [ ] Locked dependencies are used.
* [ ] Remote CI is green.

## Deployment Validation

* [ ] Frontend production artifact builds.
* [ ] Backend production artifact builds.
* [ ] Database migration succeeds in staging.
* [ ] Application refuses incompatible schema where required.
* [ ] Staging health checks pass.
* [ ] Staging smoke tests pass.
* [ ] Staging uses HTTPS.
* [ ] Staging CORS is correct.
* [ ] Release version is visible in diagnostics.
* [ ] Rollback procedure is documented and tested where practical.
* [ ] Production release still requires human approval.

## Documentation

* [ ] Runbook exists.
* [ ] Release checklist exists.
* [ ] Incident-response document exists.
* [ ] Performance baseline exists.
* [ ] Caching behavior is documented.
* [ ] Monitoring behavior is documented.
* [ ] Required commands contain no placeholders.
* [ ] Configuration variables are documented.
* [ ] Redis and PostgreSQL failure procedures are documented.
* [ ] Rollback instructions are documented.

## Review

* [ ] No unresolved P0 finding exists within Phase 5 scope.
* [ ] No unresolved P1 finding exists within Phase 5 scope.
* [ ] No unapproved critical or high security finding remains.
* [ ] `TASKS.md` reflects actual status.
* [ ] Working tree is clean.
* [ ] All Phase 5 changes are committed.
* [ ] Any required ADR has been accepted.

---

# Binary Release-Gate Rule

The final Phase 5 reviewer must return exactly one primary verdict:

* `PASS`
* `FAIL`

A `FAIL` may contain only reproducible blockers against this document.

The reviewer must not:

* Require live GoWild availability.
* Require exact Frontier taxes or fees.
* Require Frontier authentication.
* Require browser automation.
* Require user accounts.
* Require natural-language search.
* Require weather or hotel integrations.
* Require multi-region production architecture.
* Require subjective visual redesign.
* Require optional refactoring without a demonstrated defect.
* Treat an excluded future feature as a blocker.

A `PASS` requires every mandatory completion-gate item to be satisfied or explicitly marked not applicable through an accepted ADR.

---

# Reviewer Reproduction Requirements

Every blocking finding must include:

* Exact file and location
* Exact command, request, test, or load scenario
* Expected behavior
* Actual behavior
* Relevant section of this document
* Smallest compliant correction

Performance blockers must include:

* Test environment
* Dataset size
* Concurrency
* Measured p50, p95, or p99 as applicable
* Accepted target
* Reproduction command

Security blockers must include:

* Affected component
* Vulnerability or misconfiguration
* Exploitability or deployment relevance
* Scan or reproduction evidence
* Smallest remediation

A reviewer must not block the phase using:

* Pure style preference
* An excluded future requirement
* A speculative concern without reproduction
* A task status that conflicts with this active-phase contract
* A proposed architectural rewrite where a bounded correction exists

---

# Scope Rule

The active phase is defined by this file.

The presence of partial future-phase code does not make that code part of Phase 5.

`TASKS.md` records implementation status but cannot expand the active phase.

The PRD and TDD define the complete product but do not make every future requirement part of the current phase.

When incomplete future-phase code interferes with Phase 5, remove or isolate it rather than completing it.

---

# Phase 5 Exit Procedure

When the completion gate passes:

1. Confirm all required remote CI checks are green.
2. Confirm staging smoke and readiness checks pass.
3. Confirm `OPS-001` through `OPS-004` are marked `COMPLETE`.
4. Confirm `QA-001` through `QA-003` are marked `COMPLETE`.
5. Confirm later tasks remain factually marked.
6. Commit all final code and documentation changes.
7. Tag the repository:

```bash
git tag phase-5-complete
git push origin phase-5-complete
```

8. Archive this file:

```bash
cp PHASE.md docs/phases/PHASE-5-COMPLETE.md
```

9. Commit the archived contract:

```bash
git add docs/phases/PHASE-5-COMPLETE.md
git commit -m "docs: archive completed phase 5 contract"
```

10. Replace `PHASE.md` with the approved Phase 6 contract.
11. Do not deploy to production without explicit owner approval.
