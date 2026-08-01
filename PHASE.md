# Active Phase

## Phase

Phase 4 — Search API and Web Interface

## Objective

Expose the completed deterministic routing engine through a stable HTTP API and build the initial user-facing web application.

At the end of Phase 4, a user must be able to:

* Search for an origin airport by code, city, or airport name.
* Select a supported departure date.
* Configure direct or one-stop routing.
* Apply supported time, duration, geography, and estimated-price filters.
* Submit a search through the web interface.
* View deterministic itinerary results.
* Inspect flight segments, connections, local times, durations, estimated prices, availability state, and data freshness.
* Sort results.
* Preserve search state in the URL.
* Refresh or share a search URL without losing criteria.
* Understand that schedule results and estimated prices are not verified GoWild availability.
* Open Frontier to confirm availability and complete booking.

Phase 4 must use the routing engine completed in Phase 3. The frontend must not duplicate routing, timing, pricing, or availability logic.

---

# Included Tasks

Only the following tasks are included in Phase 4:

* API-001 — Implement airport search endpoint
* API-002 — Implement itinerary search endpoint
* API-003 — Implement schedule-status endpoint
* WEB-001 — Build search form
* WEB-002 — Build results list
* WEB-003 — Build itinerary card
* WEB-004 — Add filters, sorting, and URL state

No other task is part of the active phase unless this file is explicitly amended and approved.

---

# Explicitly Excluded

The following functionality is not part of Phase 4:

* Live GoWild availability
* Exact Frontier taxes and fees
* Frontier account authentication
* Frontier credential storage
* Frontier browser automation
* Official Frontier NDC integration
* Third-party live shopping integration
* Flight booking
* Payment processing
* Saved searches
* User accounts
* Notifications or alerts
* Round-trip optimization
* Multi-city routing
* More than one connection
* Flexible-date or calendar-grid search
* Natural-language search
* LLM-generated routes or prices
* AI destination recommendations
* Weather integration
* Hotel pricing
* Rental-car pricing
* Native mobile applications
* Production-scale caching
* Production rate limiting
* Full observability implementation
* Production deployment

Partial implementation of an excluded feature must not be required by Phase 4 builds, tests, or CI.

---

# Requirement Authority

Use this precedence when evaluating Phase 4 work:

1. `PHASE.md` defines the exact active scope and completion gate.
2. `DECISIONS.md` defines approved architectural decisions.
3. `docs/PRD.md` defines overall product requirements.
4. `docs/TDD.md` defines the overall technical design.
5. `TASKS.md` records task status and dependencies.

`TASKS.md` cannot expand the active phase.

An incorrectly completed future task must be corrected to its factual status. Do not implement an excluded feature merely to preserve an inaccurate task status.

When a future-state example in the PRD or TDD includes functionality excluded from Phase 4, this active-phase contract controls the current implementation.

---

# Core Design Rules

## Backend Authority

The backend is authoritative for:

* Request validation
* Airport resolution
* Schedule coverage validation
* Route generation
* Connection validation
* Timezone calculations
* Duration calculations
* Estimated pricing
* Availability status
* Filtering
* Sorting
* Itinerary identity
* Data-freshness metadata

The frontend must not independently recalculate or override these values.

Client-side sorting may be used only when it exactly follows the server-defined ordering contract and does not alter price, duration, availability, or route validity.

---

## Deterministic Search

The API must call the deterministic routing engine completed in Phase 3.

The API and frontend must not use an LLM to:

* Generate destinations
* Generate routes
* Infer flight schedules
* Calculate prices
* Validate connections
* Determine availability
* Repair malformed routing data

---

## Honest User Communication

The interface must clearly distinguish:

* Scheduled itinerary
* Estimated price
* Availability not checked
* Stale or unavailable schedule data
* No results
* Internal or provider errors

The interface must not claim:

* A flight is bookable
* A GoWild seat is available
* A displayed price is guaranteed
* A user can book for the estimated amount
* Schedule presence confirms inventory

Use language such as:

```text
Estimated GoWild cost
```

```text
Availability not checked
```

```text
Check on Frontier
```

Avoid language such as:

```text
Available now
```

```text
Book for $14.91
```

```text
Confirmed GoWild fare
```

---

# Required Phase 4 Behavior

## 1. API Versioning

All public Phase 4 API endpoints must use the versioned base path:

```text
/api/v1
```

Required endpoints:

```text
GET  /api/v1/health
GET  /api/v1/airports
POST /api/v1/search
GET  /api/v1/schedules/status
```

The existing health endpoint may remain unchanged if it already complies with the repository contract.

---

# API-001 — Airport Search Endpoint

## Endpoint

```http
GET /api/v1/airports
```

## Query Parameters

Required or supported parameters:

```text
query
limit
```

Recommended request:

```http
GET /api/v1/airports?query=atl&limit=10
```

## Required Search Behavior

Airport search must support normalized matching against:

* IATA airport code
* Airport name
* City
* State or region, when available

Matching must be:

* Case-insensitive
* Whitespace-trimmed
* Deterministic
* Limited to active airports
* Bounded by a maximum result count

Recommended priority:

1. Exact airport-code match
2. Airport-code prefix match
3. Exact city match
4. City prefix match
5. Airport-name match
6. State or region match

Stable tie-breakers must be documented.

## Validation Rules

* Empty or whitespace-only queries must either return a validated error or a documented bounded default result. Returning all airports without a strict limit is not allowed.
* `limit` must have a documented default.
* `limit` must have a documented maximum.
* Invalid limits must return HTTP 422 or the repository’s standard validation status.
* Airport codes must be serialized in uppercase.
* Inactive airports must not appear.

Recommended defaults:

```text
Default limit: 10
Maximum limit: 25
Minimum query length: 1
```

## Response Model

```json
{
  "items": [
    {
      "code": "ATL",
      "name": "Hartsfield-Jackson Atlanta International Airport",
      "city": "Atlanta",
      "state_or_region": "Georgia",
      "country_code": "US",
      "timezone": "America/New_York"
    }
  ],
  "count": 1
}
```

The response must not expose internal database identifiers unless they are intentionally part of the public contract.

---

# API-002 — Itinerary Search Endpoint

## Endpoint

```http
POST /api/v1/search
Content-Type: application/json
```

## Request Model

The request must support at least:

```json
{
  "origin": "ATL",
  "departure_date": "2026-08-04",
  "max_connections": 1,
  "min_connection_minutes": 45,
  "max_connection_minutes": 240,
  "depart_after": "06:00",
  "depart_before": "22:00",
  "arrive_before": null,
  "max_total_duration_minutes": 720,
  "max_price": 50,
  "domestic_only": false,
  "international_only": false,
  "sort": "PRICE"
}
```

Optional fields may be omitted and replaced with validated server defaults.

## Request Validation

The API must reject:

* Invalid airport-code formatting
* Unknown or inactive origin airport
* Invalid date formatting
* Date outside active schedule coverage
* Maximum connections outside `0` or `1`
* Nonpositive connection durations
* Maximum connection below minimum connection
* Invalid 24-hour time values
* Nonpositive maximum duration
* Negative maximum price
* Domestic-only and international-only both enabled
* Unsupported sort modes
* Unknown request fields when strict-schema mode is selected

The API must not begin routing before request validation succeeds.

## Search Service Integration

The endpoint must:

1. Validate the HTTP request.
2. Convert the request into the Phase 3 search-criteria domain model.
3. Identify the active schedule source.
4. Call the deterministic routing service.
5. Convert domain itineraries into public response models.
6. Include schedule-freshness metadata.
7. Return typed warnings.
8. Avoid leaking internal exceptions or provider-specific structures.

## Response Model

The response must contain at least:

```json
{
  "search_id": "7dfce768-cc8c-4a21-a4cb-fad6f4a10b97",
  "origin": {
    "code": "ATL",
    "city": "Atlanta",
    "timezone": "America/New_York"
  },
  "departure_date": "2026-08-04",
  "generated_at": "2026-08-03T21:00:00-04:00",
  "data_freshness": {
    "schedule_source": "static-schedule",
    "schedule_version": "2026-08-01",
    "schedule_updated_at": "2026-08-01T04:00:00Z",
    "schedule_effective_start": "2026-08-01",
    "schedule_effective_end": "2026-10-31",
    "availability_checked_at": null
  },
  "result_count": 1,
  "results": [
    {
      "itinerary_id": "iti_1f8b...",
      "origin": {
        "code": "ATL",
        "city": "Atlanta",
        "country_code": "US"
      },
      "destination": {
        "code": "DEN",
        "city": "Denver",
        "country_code": "US"
      },
      "departure_at": "2026-08-04T09:35:00-04:00",
      "arrival_at": "2026-08-04T11:05:00-06:00",
      "connection_count": 0,
      "total_duration_minutes": 210,
      "airborne_duration_minutes": 210,
      "total_layover_minutes": 0,
      "segments": [
        {
          "sequence": 1,
          "carrier": "F9",
          "flight_number": "1234",
          "origin": "ATL",
          "destination": "DEN",
          "departure_at": "2026-08-04T09:35:00-04:00",
          "arrival_at": "2026-08-04T11:05:00-06:00",
          "duration_minutes": 210
        }
      ],
      "price": {
        "amount": "14.91",
        "currency": "USD",
        "status": "ESTIMATED",
        "segment_count": 1,
        "verified_at": null,
        "disclaimer": "Estimated GoWild cost. Final taxes, fees, and availability must be confirmed with Frontier."
      },
      "availability": {
        "status": "NOT_CHECKED",
        "checked_at": null,
        "source": null,
        "confidence": "LOW"
      },
      "booking_url": null
    }
  ],
  "warnings": [
    {
      "code": "AVAILABILITY_NOT_CHECKED",
      "message": "GoWild availability has not been verified."
    }
  ]
}
```

## Serialization Rules

* Datetimes must be ISO 8601 strings with timezone offsets.
* Money should be serialized as a decimal-safe string unless the project has an accepted numeric serialization policy.
* Enum values must be stable public strings.
* Internal ORM models must not be serialized directly.
* Fields must not change based on whether results are empty.
* `results` must be an empty array when no itineraries match.
* `result_count` must equal the length of `results`.

## No-Result Behavior

A valid search with no matching itinerary must return a successful response unless the repository has an accepted alternative contract.

Recommended behavior:

```http
HTTP 200
```

```json
{
  "result_count": 0,
  "results": [],
  "warnings": [
    {
      "code": "NO_MATCHING_ITINERARIES",
      "message": "No scheduled itineraries matched the selected criteria."
    }
  ]
}
```

No-result searches must not be returned as HTTP 500.

---

# API-003 — Schedule Status Endpoint

## Endpoint

```http
GET /api/v1/schedules/status
```

## Required Response

```json
{
  "active": true,
  "source": "static-frontier-schedule",
  "version": "2026-08-01",
  "retrieved_at": "2026-08-01T04:00:00Z",
  "effective_start": "2026-08-01",
  "effective_end": "2026-10-31",
  "route_count": 120,
  "scheduled_flight_count": 1830
}
```

When no active schedule exists:

* Return a stable typed response or documented API error.
* Do not return a raw database error.
* Do not claim that search data is available.

The endpoint must report the same active source version used by routing searches.

---

# Public API Error Contract

All API errors must use a consistent schema.

```json
{
  "error": {
    "code": "DATE_OUTSIDE_SCHEDULE_RANGE",
    "message": "The departure date is outside the active schedule range.",
    "details": {
      "supported_start": "2026-08-01",
      "supported_end": "2026-10-31"
    },
    "request_id": "req_123"
  }
}
```

Required error categories include:

```text
INVALID_REQUEST
INVALID_AIRPORT
INVALID_DEPARTURE_DATE
DATE_OUTSIDE_SCHEDULE_RANGE
NO_ACTIVE_SCHEDULE
INVALID_CONNECTION_RANGE
INVALID_TIME_FILTER
INVALID_PRICE_FILTER
UNSUPPORTED_SORT
DATABASE_UNAVAILABLE
INTERNAL_ERROR
```

## Error Requirements

* Every error response must include a stable error code.
* Every error response must include a request ID.
* Expected validation errors must not include stack traces.
* Internal errors must not expose SQL, secrets, filesystem paths, or Python internals.
* The frontend must render expected errors differently from unexpected failures.
* API validation status codes must be documented and tested.

---

# OpenAPI Contract

FastAPI must expose:

```text
/docs
/openapi.json
```

Phase 4 must:

* Generate a valid OpenAPI schema.
* Include all Phase 4 endpoints.
* Include request and response models.
* Include error-response documentation where practical.
* Detect accidental OpenAPI contract changes in CI or review.
* Keep frontend types synchronized with the API contract.

The OpenAPI document should be checked into the repository or generated deterministically through a documented command.

---

# Frontend Architecture

## Required Routes

Minimum frontend routes:

```text
/
```

Search interface and initial state.

```text
/results
```

Search results represented through URL parameters.

```text
/data-status
```

Optional but recommended view of active schedule metadata.

An `/about` page is optional and must not block Phase 4.

---

# WEB-001 — Search Form

## Required Fields

The search form must include:

* Origin airport
* Departure date
* Maximum connections

The form must support access to these additional filters:

* Minimum connection duration
* Maximum connection duration
* Departure after
* Departure before
* Arrival before
* Maximum total duration
* Maximum estimated price
* Domestic only
* International only
* Sort mode

Advanced filters may be placed in a collapsible section.

## Airport Combobox

The airport selector must:

* Query `GET /api/v1/airports`.
* Support keyboard navigation.
* Support mouse or touch selection.
* Display airport code and city.
* Distinguish airports with similar city names.
* Debounce requests.
* Cancel or ignore stale requests.
* Show loading state.
* Show no-match state.
* Show error state.
* Store the selected airport code, not arbitrary free text.
* Prevent submission when no valid airport is selected.

Recommended display:

```text
ATL — Atlanta, Georgia
```

## Date Picker

The date picker must:

* Use a valid date input or accessible calendar component.
* Reject dates before the supported search period.
* Reject dates after active schedule coverage.
* Use the selected calendar date without timezone shifting.
* Preserve the date after navigation or refresh.
* Present the supported date range where practical.

## Form Validation

Client-side validation should improve usability but must not replace backend validation.

The form must prevent obviously invalid combinations, including:

* No selected origin
* No departure date
* Maximum connection below minimum
* Negative price
* Domestic and international both enabled

All backend validation errors must still be handled.

## Submission

Submitting the form must:

1. Serialize normalized search state.
2. Navigate to `/results`.
3. Preserve criteria in URL parameters.
4. Trigger the backend search.
5. Avoid duplicate submissions while a request is active.
6. Allow browser Back and Forward navigation.

---

# WEB-002 — Results List

The results page must support:

* Loading state
* Successful result state
* Empty-result state
* Validation-error state
* Network-error state
* Unexpected-error state
* Retry action
* Search summary
* Result count
* Data-freshness display
* Warning display
* Sorting controls
* Filter controls
* Responsive layout

Results must be rendered using itinerary cards or an equivalent accessible list structure.

The page must not require a map.

## Search Summary

The page must show:

* Origin
* Departure date
* Direct or one-stop allowance
* Active filters
* Sort mode
* Result count

## Freshness Information

The page must display or make accessible:

* Schedule source
* Schedule version
* Schedule update time
* Supported schedule range
* Availability-not-checked warning

The interface must not hide the distinction between schedule freshness and availability freshness.

---

# WEB-003 — Itinerary Card

Each itinerary card must display at least:

* Destination city
* Destination airport code
* Departure local time
* Arrival local time
* Departure date
* Arrival date when different
* Timezone context or offset where needed
* Connection count
* Total duration
* Airborne duration
* Total layover duration
* Segment flight numbers
* Segment origin and destination
* Connection airport
* Connection duration
* Estimated price
* Price status
* Availability status
* Data disclaimer
* Frontier handoff action

## Direct Itinerary

A direct itinerary must visibly indicate:

```text
Direct
```

It must not display a false connection or layover.

## One-Stop Itinerary

A one-stop itinerary must display:

* Connection airport
* Layover duration
* Both segments in chronological order
* Any date change between segments
* Total journey duration

## Price Display

Recommended:

```text
Estimated: $29.82
```

Required supporting text:

```text
Final taxes, fees, and GoWild availability must be confirmed with Frontier.
```

Do not use styling or wording that makes the estimate appear guaranteed.

## Availability Display

Phase 4 expected state:

```text
Availability not checked
```

Do not display a green “available” state for scheduled itineraries.

## Booking Handoff

Use an action such as:

```text
Check on Frontier
```

Where a stable deep link is unavailable, the action may:

* Open Frontier’s booking page.
* Present the exact origin, destination, date, and flight details needed for manual confirmation.
* Copy the search details.

The action must not claim to preserve the estimated fare.

---

# WEB-004 — Filters, Sorting, and URL State

## URL State

Search criteria must be represented in URL query parameters.

Example:

```text
/results?origin=ATL&date=2026-08-04&connections=1&sort=PRICE
```

Supported filter parameters should be documented.

Requirements:

* Refresh preserves search state.
* Shared URLs reproduce the same request criteria.
* Browser Back and Forward work.
* Invalid URL values are handled safely.
* URL state is normalized.
* Default values may be omitted when behavior remains unambiguous.
* Arbitrary URL values must not bypass backend validation.

## Filter Behavior

Changing filters must use one clearly documented strategy:

1. Submit a new backend search, or
2. Apply a client-side filter only to an already complete and equivalent result set.

Recommended Phase 4 strategy:

* Treat backend search criteria as authoritative.
* Update URL state.
* Submit a new search request.

This avoids divergence between frontend and backend semantics.

## Sort Behavior

Sorting must map directly to supported backend sort values:

```text
PRICE
TOTAL_DURATION
EARLIEST_DEPARTURE
LATEST_DEPARTURE
DESTINATION
```

Labels may be user-friendly:

```text
Lowest estimated price
Shortest trip
Earliest departure
Latest departure
Destination
```

The UI must not offer a sort mode unsupported by the API.

---

# Responsive Design

The application must work on:

* Mobile phone widths
* Tablet widths
* Desktop widths

Requirements:

* No horizontal page overflow under expected content.
* Filters remain usable on small screens.
* Itinerary details remain readable.
* Touch targets are at least 44 by 44 CSS pixels where practical.
* The primary search action remains visible and usable.
* Long airport and city names wrap safely.
* Segment timelines do not rely on fixed desktop widths.

---

# Accessibility

Phase 4 must meet WCAG 2.1 AA where practicable.

Required behaviors:

* Complete keyboard access
* Semantic form labels
* Accessible combobox behavior
* Visible focus indicators
* Screen-reader-compatible error messages
* `aria-live` or equivalent announcements for dynamic search state where appropriate
* No color-only status communication
* Sufficient text contrast
* Logical heading hierarchy
* Semantic result-list structure
* Accessible loading state
* Accessible expanded and collapsed advanced filters
* Descriptive button names
* Correct association between validation errors and controls

Automated accessibility checks must be supplemented by focused keyboard testing.

---

# Loading and Request Management

The frontend must:

* Show a loading state during searches.
* Prevent accidental duplicate submissions.
* Cancel or disregard stale autocomplete requests.
* Avoid replacing newer search results with older responses.
* Preserve existing criteria during retry.
* Handle backend timeouts and network errors.
* Avoid infinite retry loops.

Phase 4 does not require background polling.

---

# API Client and Type Synchronization

Use one documented approach:

* Generate TypeScript types from OpenAPI, or
* Maintain shared schemas with automated compatibility tests.

Recommended:

```text
OpenAPI → generated frontend API types
```

Requirements:

* Generated files must be reproducible.
* Generation command must be documented.
* CI must detect stale generated types.
* Frontend code must not define conflicting copies of API enums.
* Money, dates, optional values, and error types must be represented correctly.

---

# Security Requirements

Phase 4 must include basic web and API safeguards:

* HTTPS-compatible configuration
* Strict request validation
* Parameterized database access
* No raw SQL constructed from query input
* Safe error messages
* Configured CORS origins
* No unrestricted production CORS wildcard
* Basic secure HTTP headers
* No API keys in frontend code
* No credentials in logs
* No unsanitized rendering of backend-provided HTML
* No client-controlled database field selection
* Bounded airport-search limits
* Bounded routing request criteria

Full production rate limiting belongs to Phase 5 unless already implemented generically and correctly.

---

# Performance Requirements

Initial targets:

## Airport Search

```text
p95 under 200 ms
```

for the Phase 4 test dataset under local integration-test conditions.

## Schedule Search API

```text
p95 under 1 second
```

for direct plus one-stop searches under the agreed test dataset and environment.

## Frontend

* Search page should become interactive without unnecessary large client bundles.
* Avoid loading the complete airport dataset into the browser.
* Avoid one network request per itinerary.
* Avoid rendering unbounded result lists without a documented result limit.
* Production build must not emit critical bundle or runtime failures.

A result cap may be introduced if documented and consistently applied.

---

# Result Limits

The API must define a bounded maximum result count or a pagination strategy.

Phase 4 may use a documented maximum result count.

Recommended initial behavior:

```text
Default maximum results: 250
```

Requirements:

* Result truncation must be disclosed.
* Sorting must occur before truncation.
* The same inputs must produce the same truncated set.
* The frontend must display a warning when results are truncated.

Pagination may be deferred unless required by realistic result volume.

---

# Logging and Request IDs

API requests must include or generate a request ID.

The API should make it possible to log:

* Request ID
* Endpoint
* HTTP status
* Duration
* Origin
* Departure date
* Maximum connections
* Result count
* Active schedule version
* Error code

The frontend should include the request ID in unexpected-error diagnostic text where available.

Do not log:

* Secrets
* Full request headers
* User credentials
* Raw stack traces in user-facing responses

---

# Required Tests

## API Unit Tests

Phase 4 must include tests for:

* Airport query normalization
* Airport result ranking
* Airport limit validation
* Airport inactive-record exclusion
* Search-request conversion into domain criteria
* API response serialization
* Money serialization
* Enum serialization
* Error mapping
* Request-ID propagation
* No-result response
* Schedule-status serialization

---

## API Integration Tests

Required integration tests:

* `GET /api/v1/airports` exact code match
* Airport city match
* Airport-name match
* Case-insensitive airport search
* Airport result limit
* Invalid airport-search limit
* Search with direct results
* Search with one-stop results
* Search with filters
* Search with sort
* Search with no results
* Invalid origin
* Invalid departure date
* Date outside schedule coverage
* Invalid connection range
* Conflicting geography filters
* No active schedule
* Schedule-status endpoint
* Consistency between schedule-status source and search source
* Timezone offsets preserved
* Estimated pricing serialized correctly
* Availability remains `NOT_CHECKED`
* OpenAPI schema generation

Integration tests must use synthetic imported schedule fixtures.

---

## Frontend Unit and Component Tests

Required tests:

* Search form required fields
* Airport combobox loading state
* Airport combobox result selection
* Airport combobox keyboard navigation
* Airport combobox no-results state
* Airport combobox request error
* Date-range validation
* Connection-range validation
* Geography-filter conflict
* URL serialization
* URL deserialization
* Invalid URL fallback
* Loading-state rendering
* Error-state rendering
* Empty-state rendering
* Direct itinerary card
* One-stop itinerary card
* Cross-midnight itinerary display
* Estimated price label
* Availability-not-checked label
* Schedule-freshness display
* Result truncation warning, when applicable
* Frontier handoff wording

---

## End-to-End Tests

Phase 4 must include focused end-to-end tests for:

1. Load the search page.
2. Search for an airport by code.
3. Select an airport using the keyboard.
4. Select a supported date.
5. Submit a direct-only search.
6. View direct results.
7. Enable one-stop search.
8. Apply maximum estimated price.
9. Change sorting.
10. Refresh and preserve URL state.
11. Open a shared results URL.
12. Display a no-results state.
13. Display a backend validation error.
14. Display a network or server error.
15. Use the primary workflow at a mobile viewport.
16. Complete the primary workflow using keyboard-only navigation.

E2E tests must use stable synthetic data.

They must not call Frontier or any external live provider.

---

## Accessibility Tests

Required checks:

* Automated accessibility scan of search page
* Automated accessibility scan of populated results page
* Keyboard navigation through airport selector
* Keyboard submission
* Focus placement after validation failure
* Screen-reader-accessible status messages
* No color-only price or availability state
* Accessible advanced-filter disclosure

---

## Contract Tests

Required contract checks:

* OpenAPI generation succeeds.
* Frontend generated types match current OpenAPI.
* CI fails when generated types are stale.
* Public enum values remain stable.
* Search response matches the documented schema.
* API errors match the documented error schema.

---

# Required Test Fixtures

Phase 4 fixtures must include:

1. Multiple airports matching the same city text.
2. An exact airport-code match.
3. An inactive airport.
4. A direct itinerary.
5. A one-stop itinerary.
6. A cross-midnight itinerary.
7. Domestic and international destinations.
8. Multiple itineraries with sort ties.
9. A no-result search.
10. A schedule range boundary.
11. A source version with known freshness metadata.
12. A result set exceeding the configured result cap, when truncation is implemented.

Fixtures must be synthetic and clearly labeled.

---

# Required Verification Commands

The exact commands must be updated to match the repository.

At minimum, Phase 4 must provide commands equivalent to:

```bash
# Install
pnpm install --frozen-lockfile
<locked Python dependency installation command>

# Infrastructure and database
docker compose up -d --wait
alembic upgrade head
<fixture import command>

# Static verification
make format-check
make lint
make typecheck

# Backend tests
<backend unit-test command>
<backend integration-test command>
<API contract-test command>

# Frontend tests
pnpm --filter web test
pnpm --filter web type-check
pnpm --filter web lint

# End-to-end tests
pnpm --filter web test:e2e

# Accessibility
pnpm --filter web test
pnpm --filter web test:e2e

# API contract and generated types
cd apps/api && ./.venv/bin/python scripts/export_openapi.py
cd apps/web && pnpm gen:types
cd apps/web && pnpm check:types

# Builds
make build
pnpm --filter web build

# CI parity
<the exact commands invoked by remote CI>
```

Replace placeholders before Phase 4 is marked complete.

No agent may claim a command passed unless it was actually run.

---

# Task Status Rules

At the start of Phase 4:

* `FND-001` through `FND-008` remain `COMPLETE`.
* `DAT-001` through `DAT-006` remain `COMPLETE`.
* `RTE-001` through `RTE-007` remain `COMPLETE`.
* `API-001` through `API-003` begin as `NOT STARTED`.
* `WEB-001` through `WEB-004` begin as `NOT STARTED`.
* `OPS-*`, availability-provider, AI, and later product tasks remain `NOT STARTED`, except for generic infrastructure explicitly completed and verified in earlier phases.

A Phase 4 task may be marked `COMPLETE` only when:

* The implementation exists.
* Required tests pass.
* Public contracts are documented.
* Frontend behavior is connected to the real Phase 4 API.
* No mock-only or disconnected implementation remains in the production path.

A static UI that does not call the search API does not complete a web task.

An endpoint returning fixture constants instead of routing-engine results does not complete an API task.

---

# Allowed Change Areas

Phase 4 may modify:

```text
apps/api/**
apps/web/**
packages/**
docs/**
data/**
infrastructure/**
.github/workflows/**
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
```

Changes to Phase 3 routing behavior require:

* A demonstrated Phase 4 integration defect
* A regression test
* Confirmation that the change preserves the Phase 3 contract
* An ADR when architecture or documented semantics change

---

# Change-Control Rules

Human approval is required before:

* Modifying the PRD
* Modifying the TDD’s core architecture
* Changing public API paths
* Changing public API enum values
* Removing documented response fields
* Changing money serialization policy
* Changing timezone semantics
* Adding live availability
* Adding browser automation
* Adding Frontier authentication
* Adding an LLM dependency
* Adding user accounts
* Increasing routing above one connection
* Adding round-trip search
* Adding a paid external service
* Changing the active-phase task list
* Enabling production deployment

Approved deviations must be recorded in `DECISIONS.md`.

---

# Phase 4 Completion Gate

Phase 4 is complete only when all applicable items below are satisfied.

## Scope

* [ ] Only API-001 through API-003 and WEB-001 through WEB-004 are evaluated as Phase 4 deliverables.
* [ ] No live availability provider is required.
* [ ] No Frontier browser automation is present.
* [ ] No LLM is used for routing, pricing, or availability.
* [ ] No user account or payment implementation is required.
* [ ] Future-phase tasks remain factually marked.

## Airport API

* [ ] Airport endpoint exists under `/api/v1`.
* [ ] Exact code matching works.
* [ ] City and name matching work.
* [ ] Search is case-insensitive.
* [ ] Result ranking is deterministic.
* [ ] Inactive airports are excluded.
* [ ] Limits are validated and bounded.
* [ ] Airport API integration tests pass.

## Search API

* [ ] Search endpoint exists under `/api/v1`.
* [ ] Request validation is complete.
* [ ] Domain search criteria are used.
* [ ] Phase 3 routing engine is called.
* [ ] Direct results serialize correctly.
* [ ] One-stop results serialize correctly.
* [ ] Timezone offsets are preserved.
* [ ] Estimated pricing is serialized safely.
* [ ] Availability remains `NOT_CHECKED`.
* [ ] No-result searches return a stable response.
* [ ] Typed warnings are returned.
* [ ] Internal exceptions do not leak.

## Schedule Status

* [ ] Schedule-status endpoint exists.
* [ ] Active source metadata is correct.
* [ ] Route and flight counts are correct.
* [ ] Search and status use the same active source version.
* [ ] No-active-schedule behavior is tested.

## Error Contract

* [ ] Error schema is consistent.
* [ ] Stable error codes are used.
* [ ] Request IDs are present.
* [ ] Validation errors are distinct from internal errors.
* [ ] Stack traces and SQL details are not exposed.
* [ ] Frontend renders expected and unexpected errors appropriately.

## OpenAPI and Types

* [ ] OpenAPI generation succeeds.
* [ ] Phase 4 endpoints appear in OpenAPI.
* [ ] Frontend API types are synchronized.
* [ ] CI detects stale generated types.
* [ ] Public enum values are stable.
* [ ] Contract tests pass.

## Search Form

* [ ] Airport combobox is connected to the API.
* [ ] Airport combobox works with keyboard input.
* [ ] Date selection works.
* [ ] Supported schedule range is enforced.
* [ ] Connection selection works.
* [ ] Advanced filters work.
* [ ] Invalid combinations are prevented or clearly reported.
* [ ] Form submission produces normalized URL state.

## Results Page

* [ ] Loading state works.
* [ ] Success state works.
* [ ] Empty state works.
* [ ] Validation-error state works.
* [ ] Network-error state works.
* [ ] Retry works.
* [ ] Search summary is shown.
* [ ] Result count is shown.
* [ ] Freshness metadata is shown.
* [ ] Availability warning is shown.

## Itinerary Cards

* [ ] Direct itineraries render correctly.
* [ ] One-stop itineraries render correctly.
* [ ] Segment order is correct.
* [ ] Connection airport is shown.
* [ ] Layover duration is shown.
* [ ] Cross-midnight dates are clear.
* [ ] Local departure and arrival times are clear.
* [ ] Total duration is shown.
* [ ] Estimated price is labeled honestly.
* [ ] Availability is shown as not checked.
* [ ] Frontier handoff wording is non-misleading.

## Filters and Sorting

* [ ] Connection filter works.
* [ ] Time filters work.
* [ ] Duration filter works.
* [ ] Estimated-price filter works.
* [ ] Domestic-only works.
* [ ] International-only works.
* [ ] Sort modes map to backend values.
* [ ] URL state updates correctly.
* [ ] Refresh preserves criteria.
* [ ] Shared URL restores criteria.
* [ ] Back and Forward navigation work.
* [ ] Invalid URL parameters are handled safely.

## Responsive Design

* [ ] Primary workflow works at mobile width.
* [ ] Primary workflow works at desktop width.
* [ ] No unintended horizontal overflow exists.
* [ ] Filters remain usable on mobile.
* [ ] Long airport names render safely.
* [ ] Itinerary segments remain readable.

## Accessibility

* [ ] Search form is keyboard accessible.
* [ ] Airport combobox is accessible.
* [ ] Validation errors are associated with controls.
* [ ] Dynamic loading and result states are announced appropriately.
* [ ] Statuses do not rely on color alone.
* [ ] Focus indicators are visible.
* [ ] Automated accessibility tests pass.
* [ ] Keyboard-only E2E workflow passes.

## Tests

* [ ] API unit tests pass.
* [ ] API integration tests pass.
* [ ] Frontend unit and component tests pass.
* [ ] End-to-end tests pass.
* [ ] Accessibility checks pass.
* [ ] Contract tests pass.
* [ ] Tests use synthetic data.
* [ ] No test calls Frontier or an external live provider.
* [ ] Defect fixes include regression tests.

## Performance

* [ ] Airport-search performance meets the agreed target or has an accepted exception.
* [ ] Search API performance meets the agreed target or has an accepted exception.
* [ ] No request is made per itinerary card.
* [ ] No complete airport dataset is shipped unnecessarily to the browser.
* [ ] Result count is bounded or paginated.
* [ ] Truncation is disclosed when applicable.

## Security

* [ ] Request inputs are strictly validated.
* [ ] CORS origins are configured.
* [ ] No production wildcard CORS is used.
* [ ] Secure HTTP headers are configured.
* [ ] Secrets are absent from frontend bundles.
* [ ] Backend errors do not expose internal data.
* [ ] User-controlled text is rendered safely.
* [ ] Airport and result limits are bounded.

## Verification

* [ ] Formatting passes.
* [ ] Lint passes.
* [ ] Backend type checking passes.
* [ ] Frontend type checking passes.
* [ ] Backend tests pass.
* [ ] Frontend tests pass.
* [ ] E2E tests pass.
* [ ] Accessibility tests pass.
* [ ] OpenAPI and type-generation checks pass.
* [ ] Production builds pass.
* [ ] Docker Compose validates.
* [ ] PostgreSQL and Redis become healthy.
* [ ] Remote CI is green.

## Review

* [ ] No unresolved P0 finding exists within Phase 4 scope.
* [ ] No unresolved P1 finding exists within Phase 4 scope.
* [ ] `TASKS.md` reflects actual status.
* [ ] Working tree is clean.
* [ ] All Phase 4 changes are committed.
* [ ] Any required ADR has been accepted.

---

# Binary Release-Gate Rule

The final Phase 4 reviewer must return exactly one primary verdict:

* `PASS`
* `FAIL`

A `FAIL` may contain only reproducible blockers against this document.

The reviewer must not:

* Require live GoWild availability.
* Require exact taxes or fees.
* Require Frontier authentication.
* Require browser automation.
* Require user accounts.
* Require alerts.
* Require weather or hotel data.
* Require round-trip search.
* Require natural-language search.
* Require production deployment.
* Require optional visual redesigns.
* Treat subjective styling preferences as blockers.

A `PASS` requires every mandatory completion-gate item to be satisfied or explicitly marked not applicable through an accepted ADR.

---

# Reviewer Reproduction Requirements

Every blocking finding must include:

* Exact file and location
* Exact failed command, request, or test
* Expected behavior
* Actual behavior
* Relevant section of this document
* Smallest compliant correction

A reviewer must not block the phase using:

* A subjective style preference
* An excluded future requirement
* A speculative concern without reproduction
* A task status that conflicts with this contract
* A broad redesign where a bounded correction exists

---

# Scope Rule

The active phase is defined by this file.

The presence of partial future-phase code does not make that code part of Phase 4.

`TASKS.md` records implementation status but cannot expand the active phase.

The PRD and TDD define the complete product but do not make every future requirement part of the current phase.

When incomplete future-phase code interferes with Phase 4, remove or isolate it rather than completing it.

---

# Phase 4 Exit Procedure

When the completion gate passes:

1. Confirm all remote CI checks are green.
2. Confirm `API-001` through `API-003` are marked `COMPLETE`.
3. Confirm `WEB-001` through `WEB-004` are marked `COMPLETE`.
4. Confirm later tasks remain factually marked.
5. Commit all final code and documentation changes.
6. Tag the repository:

```bash
git tag phase-4-complete
git push origin phase-4-complete
```

7. Archive this file:

```bash
cp PHASE.md docs/phases/PHASE-4-COMPLETE.md
```

8. Commit the archived contract:

```bash
git add docs/phases/PHASE-4-COMPLETE.md
git commit -m "docs: archive completed phase 4 contract"
```

9. Replace `PHASE.md` with the approved Phase 5 contract.
