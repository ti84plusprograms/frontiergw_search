# Active Phase

## Phase

Phase 3 — Deterministic Routing Engine

## Objective

Build the deterministic flight-routing engine that converts normalized schedule definitions into dated, timezone-aware itineraries.

At the end of this phase, the backend must be able to:

* Resolve scheduled flights for a specific operating date.
* Generate valid direct itineraries.
* Generate valid one-stop itineraries.
* Validate connection timing.
* Prevent circular and duplicate itineraries.
* Calculate flight, layover, and total journey durations.
* Apply deterministic filters and sorting.
* Attach clearly labeled estimated GoWild pricing.
* Return routing-domain results through tested service interfaces.

This phase does not implement the public search API, production frontend search experience, live Frontier availability, or AI-assisted search.

---

# Included Tasks

Only the following tasks are included in Phase 3:

* RTE-001 — Build timezone-aware flight instances
* RTE-002 — Implement direct itinerary search
* RTE-003 — Implement one-stop itinerary search
* RTE-004 — Implement connection validation
* RTE-005 — Implement itinerary deduplication
* RTE-006 — Implement filters and sorting
* RTE-007 — Implement estimated pricing

No other task is part of the active phase unless this file is explicitly amended and approved.

---

# Explicitly Excluded

The following functionality is not part of Phase 3:

* Public destination-search API
* Airport-search API
* Production search form
* Search-results UI
* Map interface
* User accounts
* Saved searches
* Round-trip optimization
* Multi-city routing
* More than one connection
* Live GoWild availability
* Exact taxes and fees
* Frontier account authentication
* Frontier browser automation
* Official Frontier or NDC integration
* Third-party live flight shopping
* Natural-language search
* LLM-based route generation
* Weather integration
* Hotel pricing
* Notifications
* Production deployment
* Full product end-to-end tests

Partial implementation of an excluded feature must not be required by Phase 3 builds, tests, migrations, or CI.

---

# Requirement Authority

Use this precedence when evaluating Phase 3 work:

1. `PHASE.md` defines the exact active scope and completion gate.
2. `DECISIONS.md` defines approved architectural decisions.
3. `docs/PRD.md` defines overall product requirements.
4. `docs/TDD.md` defines the overall technical design.
5. `TASKS.md` records task status and dependencies.

`TASKS.md` cannot expand the active phase.

A future task marked `COMPLETE` incorrectly must be corrected to its factual status. Do not implement an excluded feature merely to preserve an inaccurate task status.

When this document conflicts with a general future-state example in the TDD, this active-phase contract controls Phase 3 scope. The conflict must still be documented if it affects the eventual architecture.

---

# Core Design Rules

## Deterministic Execution

Routing must be implemented with deterministic application logic.

The routing engine must not use an LLM to:

* Select flights
* Generate routes
* Calculate dates or times
* Validate connections
* Calculate duration
* Calculate price
* Determine availability
* Deduplicate itineraries
* Rank results

Given the same schedule dataset, configuration, search criteria, and clock-independent inputs, the engine must return the same results in the same order.

---

## Timezone Awareness

All resolved flight-instance datetimes must be timezone-aware.

The implementation must:

* Use IANA timezone identifiers from airport metadata.
* Interpret departure wall-clock time in the origin airport timezone.
* Interpret arrival wall-clock time in the destination airport timezone.
* Apply `arrival_day_offset` before resolving the destination datetime.
* Calculate elapsed duration using absolute instants.
* Preserve local timezone offsets in domain serialization where applicable.
* Reject or quarantine schedules with invalid or missing timezone data.
* Avoid naive datetime arithmetic.

UTC may be used internally for comparisons, but local airport time and timezone must remain available.

---

## Exact Money Representation

Estimated pricing must not use binary floating-point arithmetic.

Use one of:

* Python `Decimal`
* Integer minor units
* PostgreSQL `NUMERIC`, if persisted

Estimated and verified pricing must remain distinct concepts.

Phase 3 implements only estimated pricing.

---

# Required Phase 3 Behavior

## 1. Search Criteria Domain Model

The routing engine must define a validated search-criteria model containing at least:

* Origin airport code
* Departure date
* Maximum connections
* Minimum connection duration
* Maximum connection duration
* Optional departure-after time
* Optional departure-before time
* Optional arrival-before time
* Optional maximum total duration
* Optional maximum estimated price
* Optional domestic-only filter
* Optional international-only filter
* Sort mode

Requirements:

* Origin airport code is normalized to uppercase.
* Maximum connections is limited to `0` or `1`.
* Minimum connection duration is positive.
* Maximum connection duration exceeds or equals the minimum.
* Maximum total duration is positive when present.
* Maximum price is nonnegative when present.
* Domestic-only and international-only cannot both be enabled.
* Invalid criteria fail before schedule traversal begins.

This phase may define backend-only Pydantic or domain models. A public HTTP request schema is not required.

---

## 2. Flight-Instance Resolution

A scheduled-flight definition must be resolvable into a dated flight instance.

The resolved flight instance must contain at least:

* Scheduled-flight identifier
* Carrier code
* Flight number
* Origin airport code
* Destination airport code
* Timezone-aware departure datetime
* Timezone-aware arrival datetime
* Duration in minutes
* Operating date
* Source-version reference or traceability identifier

Resolution must verify:

* The selected date is within the schedule’s effective range.
* The selected ISO weekday is present in `operating_days`.
* Origin and destination airports exist.
* Both airports have valid IANA timezones.
* Departure and arrival wall-clock times are valid.
* Arrival occurs after departure as an absolute instant.
* Computed duration is positive.
* `arrival_day_offset` is applied correctly.

A schedule definition that does not operate on the requested date must not produce a flight instance.

---

## 3. Effective-Date Handling

A scheduled flight is applicable only when:

```text
effective_start <= operating_date
```

and either:

```text
effective_end is null
```

or:

```text
operating_date <= effective_end
```

Tests must cover:

* Exact effective-start boundary
* Exact effective-end boundary
* One day before effective start
* One day after effective end
* Open-ended schedules
* Conflicting or duplicate schedule definitions

---

## 4. Weekday Handling

Weekdays must use ISO values:

* Monday: 1
* Tuesday: 2
* Wednesday: 3
* Thursday: 4
* Friday: 5
* Saturday: 6
* Sunday: 7

The engine must determine weekday applicability from the requested operating date, not from UTC conversion.

---

## 5. Direct Itinerary Generation

For a valid search origin and date, the routing engine must:

1. Retrieve applicable scheduled flights departing from the origin.
2. Resolve each into a flight instance.
3. Apply segment-level search filters.
4. Create one-segment itineraries.
5. Calculate itinerary-level duration values.
6. Attach estimated price.
7. Deduplicate equivalent results.
8. Return results in deterministic order.

Each direct itinerary must include:

* Deterministic itinerary ID
* Origin
* Destination
* Departure datetime
* Arrival datetime
* One ordered segment
* Connection count of `0`
* Total duration
* Airborne duration
* Layover duration of `0`
* Estimated price summary
* Availability status of `NOT_CHECKED`

A direct itinerary must not be generated when the destination equals the origin.

---

## 6. One-Stop Itinerary Generation

When `max_connections` is `1`, the engine must generate valid two-segment itineraries.

For each valid first segment:

1. Identify scheduled flights departing from the first segment’s destination.
2. Consider departures on the connection airport’s applicable local date.
3. Consider the following local date where needed for after-midnight departures.
4. Resolve second-segment candidates into timezone-aware instances.
5. Calculate the layover as:

```text
second departure instant - first arrival instant
```

6. Validate the connection.
7. Construct an itinerary when all rules pass.

A valid one-stop itinerary must satisfy all of the following:

* Exactly two segments
* Exactly one connection
* Second origin equals first destination
* Second departure occurs after first arrival
* Layover is within configured limits
* Final destination differs from original origin
* Final destination differs from connection airport
* No airport repeats in the path
* No segment is duplicated
* Total duration is positive
* Total duration is within configured limits
* The second flight operates on its resolved departure date

---

## 7. Connection-Date Resolution

The engine must correctly distinguish:

* Same-calendar-day connections
* Connections crossing midnight
* Connections where airport timezones differ
* Arrivals whose local date differs from departure date
* Second segments operating on the next local day

The implementation must not assume that both segments share the same date or timezone.

Candidate second-segment operating dates should be derived from the connection airport’s local arrival date and the configured connection window.

The implementation may inspect more than two local dates if required by an accepted connection-window policy, but Phase 3 does not require overnight layovers longer than the configured maximum.

---

## 8. Connection Validation

Default configuration, unless superseded by an accepted ADR:

```text
Minimum connection: 45 minutes
Maximum connection: 240 minutes
Maximum total duration: 720 minutes
Maximum connections: 1
Overnight connection support: only when the elapsed layover remains within the configured maximum
```

Connection validation must reject:

* Negative layovers
* Zero-duration layovers
* Layovers below the minimum
* Layovers above the maximum
* Second departure before first arrival
* Repeated airports
* Return to the original origin
* Duplicate segments
* Invalid second-segment operating dates
* Total duration above the configured maximum
* Invalid timezone information
* Impossible or nonpositive segment durations

Boundary behavior must be explicit and tested.

Recommended inclusive rules:

```text
layover >= minimum connection
layover <= maximum connection
total duration <= maximum total duration
```

---

## 9. Airport-Path Rules

For Phase 3, an itinerary airport path must be acyclic.

Valid examples:

```text
ATL → DEN
ATL → DEN → LAS
```

Invalid examples:

```text
ATL → ATL
ATL → DEN → ATL
ATL → DEN → DEN
ATL → DEN → ATL → LAS
```

The last example is also outside Phase 3 because it contains more than one connection.

---

## 10. Duration Calculations

The itinerary domain model must calculate at least:

* Segment duration for each segment
* Total airborne duration
* Total layover duration
* Total itinerary duration

Definitions:

```text
segment duration =
segment arrival instant - segment departure instant
```

```text
total airborne duration =
sum of segment durations
```

```text
total layover duration =
sum of time between adjacent segments
```

```text
total itinerary duration =
final arrival instant - initial departure instant
```

The following invariant must hold:

```text
total itinerary duration =
total airborne duration + total layover duration
```

Allow only a documented rounding tolerance if durations are represented below minute precision. Prefer exact minute arithmetic after validating source precision.

---

## 11. Deterministic Itinerary Identity

Every itinerary must receive a deterministic identity.

The identity must be based on stable itinerary-defining fields, including:

* Operating date
* Ordered carrier codes
* Ordered flight numbers
* Ordered origin and destination codes
* Ordered departure timestamps
* Ordered arrival timestamps, if required to avoid collisions

Recommended derivation:

```text
SHA-256 of a canonical serialized segment signature
```

Canonical serialization must:

* Use stable field ordering.
* Use timezone-aware ISO 8601 values or normalized UTC instants.
* Avoid locale-dependent formatting.
* Avoid random identifiers.
* Produce the same hash across repeated executions.

Equivalent itineraries must produce the same itinerary ID.

Materially different itineraries must produce different IDs.

---

## 12. Deduplication

The engine must remove equivalent duplicate itineraries.

Duplicate schedules may arise from:

* Reimported provider records
* Overlapping effective schedule definitions
* Multiple active records representing the same operation
* Provider normalization errors
* Equivalent route-generation paths

Deduplication must occur using deterministic segment identity or itinerary identity.

When duplicate candidates contain conflicting metadata, the engine must:

* Apply a documented precedence rule, or
* Reject the conflicting candidates, or
* Produce a diagnostic that prevents silent arbitrary selection

The selected rule must be tested.

Deduplication must not collapse:

* Different departure times
* Different flight numbers
* Different connection airports
* Different operating dates
* Different segment sequences

---

## 13. Filtering

Phase 3 must support deterministic filtering for at least:

* Maximum connections
* Departure after
* Departure before
* Arrival before
* Maximum total duration
* Maximum estimated price
* Domestic only
* International only

Optional filters may be added only when they do not expand into future product features.

Time-filter semantics must be documented.

Recommended behavior:

* Departure filters apply to the itinerary’s initial departure in the origin airport’s local time.
* Arrival-before applies to the itinerary’s final arrival in the destination airport’s local time.
* Duration filters use elapsed minutes.
* Price filters use estimated itinerary total.
* Domestic-only requires the destination country to match the origin country.
* International-only requires the destination country to differ from the origin country.

Segment-level versus itinerary-level filtering must not be ambiguous.

---

## 14. Sorting

Phase 3 must support deterministic sorting by at least:

* Estimated price
* Shortest total duration
* Earliest departure
* Latest departure
* Destination code or alphabetical destination

Recommended sort identifiers:

```text
PRICE
TOTAL_DURATION
EARLIEST_DEPARTURE
LATEST_DEPARTURE
DESTINATION
```

Each sort must define stable tie-breakers.

Recommended tie-breaker sequence:

1. Primary selected sort field
2. Connection count
3. Total duration
4. Initial departure instant
5. Destination code
6. Itinerary ID

The same input dataset and criteria must return the same ordering.

---

## 15. Estimated Pricing

The Phase 3 pricing service must calculate a configurable estimated amount per itinerary segment.

Default configuration, unless changed through an accepted ADR:

```text
Domestic estimated segment price: USD 14.91
International estimation: disabled
```

Estimated domestic itinerary price:

```text
segment count × configured domestic estimated segment price
```

Examples:

```text
One domestic segment:
1 × 14.91 = USD 14.91
```

```text
Two domestic segments:
2 × 14.91 = USD 29.82
```

Requirements:

* Use exact decimal arithmetic.
* Include currency.
* Include segment count.
* Use price status `ESTIMATED`.
* Include an explicit disclaimer.
* Do not populate verified timestamps.
* Do not claim current availability.
* Do not estimate international pricing unless explicitly enabled by configuration.
* Unknown or disabled estimates must remain `null` or use an explicit unknown state rather than zero.

---

## 16. Price Summary Domain Model

The routing result must support a price summary containing at least:

* Amount, when available
* Currency
* Status
* Segment count
* Base amount, when applicable
* Taxes and fees, when applicable
* Verified-at timestamp
* Disclaimer

Phase 3 expected values:

```text
status = ESTIMATED
verified_at = null
availability = NOT_CHECKED
```

The architecture must permit future verified pricing without changing the fundamental itinerary model.

---

## 17. Availability State

All Phase 3 itineraries must use:

```text
availability status = NOT_CHECKED
```

Phase 3 must not infer availability from schedule existence.

A scheduled itinerary means only that the route is theoretically represented by the active schedule dataset.

The engine must not use labels such as:

* Available
* Bookable
* Confirmed
* Live
* Guaranteed

---

## 18. Repository and Service Boundaries

Recommended backend boundaries:

```text
domain/
  search_criteria.py
  flight_instance.py
  itinerary.py
  pricing.py
  enums.py

repositories/
  schedule_repository.py

services/
  flight_instance_resolver.py
  routing_service.py
  connection_validator.py
  itinerary_deduplicator.py
  itinerary_filter.py
  itinerary_sorter.py
  price_estimator.py
```

Exact file names may vary.

Requirements:

* Database queries remain in repositories.
* Routing rules remain in domain or service layers.
* Provider-specific code remains outside routing services.
* API and frontend concerns do not enter the routing engine.
* Core services must be testable without an HTTP server.
* Unit tests should not require external network access.

---

# Search Algorithm Requirements

## Direct Search Flow

The direct-search flow must be equivalent to:

```text
Validate criteria
↓
Load applicable first-segment schedule definitions
↓
Resolve dated flight instances
↓
Reject invalid instances
↓
Apply first-segment filters
↓
Construct direct itineraries
↓
Attach estimated pricing
↓
Deduplicate
↓
Apply itinerary-level filters
↓
Sort deterministically
↓
Return results
```

---

## One-Stop Search Flow

The one-stop flow must be equivalent to:

```text
Generate valid first segments
↓
Determine valid connection-airport local date range
↓
Load second-segment schedule candidates
↓
Resolve second-segment instances
↓
Validate chronology
↓
Validate connection duration
↓
Validate airport path
↓
Validate total duration
↓
Construct one-stop itinerary
↓
Attach estimated pricing
↓
Deduplicate
↓
Apply itinerary-level filters
↓
Sort deterministically
↓
Return results
```

---

## Reference Pseudocode

```python
def search_itineraries(
    criteria: SearchCriteria,
) -> list[Itinerary]:
    criteria.validate()

    first_definitions = schedule_repository.find_departures(
        origin=criteria.origin,
        operating_date=criteria.departure_date,
    )

    itineraries: list[Itinerary] = []

    first_instances = resolve_applicable_instances(
        first_definitions,
        criteria.departure_date,
    )

    for first in first_instances:
        if not first_segment_filter.matches(first, criteria):
            continue

        direct = itinerary_factory.build_direct(first)

        if itinerary_filter.matches(direct, criteria):
            itineraries.append(direct)

        if criteria.max_connections == 0:
            continue

        candidate_dates = connection_date_service.candidate_dates(
            first=first,
            max_connection_minutes=criteria.max_connection_minutes,
        )

        second_definitions = schedule_repository.find_departures_for_dates(
            origin=first.destination_code,
            operating_dates=candidate_dates,
        )

        second_instances = resolve_candidate_instances(
            second_definitions,
            candidate_dates,
        )

        for second in second_instances:
            validation = connection_validator.validate(
                first=first,
                second=second,
                criteria=criteria,
            )

            if not validation.is_valid:
                continue

            itinerary = itinerary_factory.build_one_stop(
                first=first,
                second=second,
            )

            if itinerary_filter.matches(itinerary, criteria):
                itineraries.append(itinerary)

    itineraries = price_estimator.attach_estimates(itineraries)
    itineraries = itinerary_deduplicator.deduplicate(itineraries)
    itineraries = itinerary_sorter.sort(itineraries, criteria.sort)

    return itineraries
```

This pseudocode is illustrative. The implementation may optimize query order, but must preserve behavior and testability.

---

# Performance Requirements

Phase 3 is a backend-domain phase, but the routing engine must be designed for the eventual API latency target.

Initial performance targets:

* Direct search for a major origin: under 250 ms at p95 in a local integration benchmark
* Direct plus one-stop search: under 1 second at p95 for the seeded test-scale dataset
* No unbounded traversal
* No loading of the entire global schedule dataset when indexed origin/date queries suffice
* No per-result database query pattern that creates uncontrolled N+1 behavior

The benchmark environment and dataset size must be documented.

A benchmark failure does not automatically block Phase 3 unless it reveals an algorithmic or database-access defect. The final gate should use the agreed test dataset and environment.

---

# Required Database and Repository Behavior

## Schedule Queries

The schedule repository must support queries equivalent to:

* Applicable departures from one origin on one date
* Applicable departures from one origin over a bounded set of dates
* Airport metadata retrieval for involved airports
* Active source-version filtering

Routing queries must not mix inactive schedule versions into results.

---

## Active Dataset Rule

Unless an accepted ADR defines otherwise, the routing engine must use only the active schedule dataset.

It must not combine records from prior inactive versions.

Tests must verify that activating a new schedule version changes routing results without retaining obsolete active flights.

---

## Read-Only Routing

Phase 3 routing operations must be read-only with respect to schedule data.

The routing engine may create in-memory domain objects but must not mutate:

* Airports
* Routes
* Scheduled flights
* Data-source versions

Persistence of search events, itinerary caches, or availability snapshots belongs to later phases unless explicitly approved.

---

# Required Tests

## Unit Tests

Phase 3 must include unit tests for:

### Search Criteria

* Airport-code normalization
* Maximum-connections validation
* Connection-range validation
* Duration validation
* Price validation
* Domestic/international mutual exclusion
* Time-filter parsing

### Flight Instances

* Same-timezone flight
* Eastbound timezone change
* Westbound timezone change
* Arrival-day offset zero
* Arrival-day offset one
* Positive duration validation
* Invalid negative duration
* Missing timezone
* Invalid timezone
* Effective-start boundary
* Effective-end boundary
* Weekday applicability

### Direct Itineraries

* Valid one-segment itinerary
* Connection count equals zero
* Layover duration equals zero
* Origin-to-origin rejection
* Deterministic itinerary ID
* Stable repeated execution

### One-Stop Itineraries

* Valid same-day connection
* Valid cross-midnight connection
* Connection in a different timezone
* Minimum connection boundary
* Maximum connection boundary
* Below-minimum rejection
* Above-maximum rejection
* Return-to-origin rejection
* Repeated-connection-airport rejection
* Duplicate-segment rejection
* Invalid second-segment operating date
* Total-duration rejection

### Duration Calculations

* Airborne duration sum
* Layover duration sum
* Total-duration invariant
* Multi-timezone elapsed duration
* After-midnight elapsed duration

### Deduplication

* Exact duplicate collapse
* Stable winner selection
* Different departure times preserved
* Different flight numbers preserved
* Different connection airports preserved
* Different dates preserved
* Conflicting duplicate handling

### Filters

* Direct-only
* Departure-after boundary
* Departure-before boundary
* Arrival-before boundary
* Maximum-duration boundary
* Maximum-price boundary
* Domestic-only
* International-only
* Combined filters

### Sorting

* Price sort
* Duration sort
* Earliest-departure sort
* Latest-departure sort
* Destination sort
* Stable tie-breakers
* Repeatable ordering

### Pricing

* One-segment estimate
* Two-segment estimate
* Decimal precision
* Disabled international estimate
* Null or unknown estimate handling
* Estimated status
* Required disclaimer
* Availability remains not checked

---

## Integration Tests

Phase 3 must include integration tests using PostgreSQL and the Phase 2 import pipeline for:

* Search against the active schedule version
* Direct results from an origin/date query
* One-stop results from an origin/date query
* Inactive source records excluded
* New active source version changes results
* Effective-date filtering
* Weekday filtering
* Cross-midnight connection
* Timezone-aware durations
* Duplicate database records deduplicated safely
* Domestic and international filtering
* Sorting against persisted schedule data
* No-result search
* Invalid-origin handling at the service boundary
* Search using a clean migrated database populated through fixtures

---

## Property-Based Tests

Use property-based testing for core invariants where practical.

Required properties include:

* Every returned itinerary has one or two segments.
* Connection count equals segment count minus one.
* Segments are ordered chronologically.
* Every segment arrival occurs after its departure.
* Every connection departure occurs after the preceding arrival.
* No airport repeats in an itinerary.
* Final destination differs from original origin.
* Total duration is positive.
* Total duration equals airborne plus layover duration.
* Estimated domestic price is monotonic with segment count under fixed configuration.
* Equivalent itinerary inputs produce identical IDs.
* Deduplication is idempotent.
* Sorting is deterministic.

---

# Required Test Fixtures

Fixtures must include at least:

1. A direct domestic route.
2. A direct international route.
3. A valid one-stop domestic itinerary.
4. A valid one-stop international itinerary.
5. A connection exactly at the minimum boundary.
6. A connection exactly at the maximum boundary.
7. A connection one minute below minimum.
8. A connection one minute above maximum.
9. A connection crossing midnight.
10. A westbound timezone example.
11. An eastbound timezone example.
12. A daylight-saving transition example.
13. A return-to-origin route.
14. A repeated-airport route.
15. Duplicate schedule records.
16. Overlapping effective schedule records.
17. Two schedule-source versions with different active flights.
18. A result set with sorting ties.
19. A flight with arrival-day offset one.
20. A route exceeding maximum total duration.

Fixtures must remain clearly labeled as synthetic test data and must not be represented as current Frontier inventory.

---

# Daylight-Saving-Time Tests

Tests must cover at least:

* A flight on a spring-forward date
* A flight on a fall-back date
* A route between a DST-observing airport and a non-DST airport
* An ambiguous local time where the timezone library requires explicit handling
* A nonexistent local time during spring transition

The implementation must define how ambiguous or nonexistent source times are handled.

Recommended rule:

* Reject ambiguous or nonexistent schedule instances unless the source provides enough information to resolve them deterministically.

Any alternative requires an accepted ADR and explicit tests.

---

# Error and Diagnostic Requirements

Routing failures must distinguish between:

* Invalid search criteria
* Unknown origin airport
* Origin with invalid timezone metadata
* No active schedule dataset
* Date outside active schedule coverage
* No applicable departures
* Invalid schedule record
* No valid itineraries after filtering
* Internal routing invariant failure

Expected no-result cases must not be treated as internal server errors.

The service layer should return typed results or typed domain exceptions suitable for later API translation.

---

# Logging and Observability

Phase 3 search operations must make it possible to record:

* Search origin
* Departure date
* Maximum connections
* Number of first-segment candidates
* Number of second-segment candidates
* Number of rejected connections
* Number of deduplicated itineraries
* Final result count
* Search duration
* Active source version
* Failure category

Sensitive or user-identifying data must not be logged.

Structured logging may be implemented directly or prepared through a clean service interface if full observability belongs to a later phase.

---

# Configuration Requirements

Phase 3 must define documented configuration for at least:

```text
DEFAULT_MIN_CONNECTION_MINUTES
DEFAULT_MAX_CONNECTION_MINUTES
DEFAULT_MAX_TOTAL_DURATION_MINUTES
DOMESTIC_ESTIMATED_SEGMENT_PRICE_USD
INTERNATIONAL_ESTIMATION_ENABLED
MAX_SUPPORTED_CONNECTIONS
```

Requirements:

* Defaults must be centralized.
* Environment values must be validated.
* Invalid configuration must fail clearly at startup or service initialization.
* Tests must not depend on uncontrolled developer-machine environment variables.
* Test configuration must be explicit.

---

# Required Verification Commands

The authoritative commands must be recorded here once confirmed by the repository.

At minimum, Phase 3 must have commands equivalent to:

```bash
# Install
pnpm install --frozen-lockfile
<locked Python dependency installation command>

# Static checks
make format-check
make lint
make typecheck

# Database and fixtures
docker compose up -d --wait
alembic upgrade head
<Phase 2 fixture import command>

# Tests
<backend unit-test command>
<backend integration-test command>
<property-based test command or included suite>
<routing-focused test command>

# Performance
<routing benchmark or performance-test command>

# Build
make build

# CI parity
<the same commands invoked by remote CI>
```

Replace placeholders with actual working repository commands before Phase 3 is marked complete.

No agent may claim a command passed unless it was actually executed successfully.

---

# Task Status Rules

At the start of Phase 3:

* `FND-001` through `FND-008` remain `COMPLETE`.
* `DAT-001` through `DAT-006` remain `COMPLETE`.
* `RTE-001` through `RTE-007` begin as `NOT STARTED`.
* All `API-*`, `WEB-*`, `OPS-*`, and future `QA-*` tasks remain `NOT STARTED`, except for infrastructure or test tasks explicitly completed and verified in prior phases.
* A routing task may be marked `IN PROGRESS` only while active implementation exists.
* A routing task may be marked `COMPLETE` only when its implementation and required tests pass.
* Partial algorithm implementation is not completion.
* Unit tests without integration behavior do not complete the corresponding task.
* Implementation without boundary and timezone tests does not complete the corresponding task.
* A future API or UI task must not be marked complete merely because a temporary internal interface exists.

---

# Allowed Change Areas

Phase 3 may modify:

```text
apps/api/**
data/**
docs/**
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
lockfiles
```

Frontend files under `apps/web/**` should be modified only when required to preserve builds or generic developer configuration.

Phase 3 must not introduce the product search interface or itinerary-results UI.

---

# Change-Control Rules

Human approval is required before:

* Modifying the PRD
* Modifying the TDD’s core architecture
* Increasing maximum supported connections above one
* Adding round-trip search
* Adding multi-city search
* Adding live Frontier availability
* Adding browser automation
* Adding an LLM dependency
* Changing the active schedule-version rule
* Changing timezone-resolution policy
* Changing money representation
* Persisting generated itineraries
* Introducing a new database technology
* Adding a paid external provider
* Changing the active-phase task list
* Enabling production deployment

Approved deviations must be recorded in `DECISIONS.md`.

---

# Phase 3 Completion Gate

Phase 3 is complete only when all of the following are true.

## Scope

* [ ] Only RTE-001 through RTE-007 are evaluated as Phase 3 deliverables.
* [ ] No public search API is required by Phase 3 CI.
* [ ] No production frontend search interface is required.
* [ ] No live availability provider has been added.
* [ ] No browser automation has been added.
* [ ] No LLM is used in routing or pricing.
* [ ] Future-phase tasks remain factually marked.

## Search Criteria

* [ ] Search-criteria domain model exists.
* [ ] Invalid criteria are rejected deterministically.
* [ ] Maximum connections is limited to zero or one.
* [ ] Connection-duration constraints are validated.
* [ ] Geographic filter conflicts are rejected.

## Flight Instances

* [ ] Scheduled flights resolve into timezone-aware dated instances.
* [ ] Effective-date rules are correct.
* [ ] ISO weekday rules are correct.
* [ ] Arrival-day offset is correct.
* [ ] Computed durations are positive.
* [ ] Invalid timezone data is handled explicitly.

## Direct Routing

* [ ] Direct itineraries are generated correctly.
* [ ] Direct itineraries contain exactly one segment.
* [ ] Direct itinerary duration values are correct.
* [ ] Origin-to-origin results are excluded.
* [ ] Direct itinerary IDs are deterministic.

## One-Stop Routing

* [ ] Valid one-stop itineraries are generated.
* [ ] Same-day connections work.
* [ ] Cross-midnight connections work.
* [ ] Timezone-different connections work.
* [ ] Invalid short connections are rejected.
* [ ] Invalid long connections are rejected.
* [ ] Return-to-origin routes are rejected.
* [ ] Repeated-airport routes are rejected.
* [ ] Total-duration limits are enforced.
* [ ] Second-segment operating dates are correct.

## Duration Invariants

* [ ] Every segment duration is positive.
* [ ] Every layover duration is valid.
* [ ] Total airborne duration is correct.
* [ ] Total layover duration is correct.
* [ ] Total duration equals airborne plus layover duration.

## Deduplication

* [ ] Equivalent itineraries collapse deterministically.
* [ ] Distinct itineraries remain distinct.
* [ ] Duplicate handling is documented.
* [ ] Deduplication is idempotent.
* [ ] Conflicting duplicates are not selected arbitrarily.

## Filtering

* [ ] Connection filtering works.
* [ ] Departure-time filters work.
* [ ] Arrival-time filter works.
* [ ] Maximum-duration filter works.
* [ ] Maximum-price filter works.
* [ ] Domestic-only filter works.
* [ ] International-only filter works.
* [ ] Combined filters work.

## Sorting

* [ ] Price sorting works.
* [ ] Duration sorting works.
* [ ] Earliest-departure sorting works.
* [ ] Latest-departure sorting works.
* [ ] Destination sorting works.
* [ ] Tie-breakers are stable.
* [ ] Repeated searches produce the same ordering.

## Estimated Pricing

* [ ] One-segment estimated pricing is correct.
* [ ] Two-segment estimated pricing is correct.
* [ ] Exact decimal arithmetic is used.
* [ ] Estimated status is explicit.
* [ ] Verified timestamp is absent.
* [ ] Availability remains `NOT_CHECKED`.
* [ ] International estimate behavior is explicit.
* [ ] Disclaimer is present.

## Timezone and DST

* [ ] Eastbound timezone test passes.
* [ ] Westbound timezone test passes.
* [ ] Cross-midnight test passes.
* [ ] Spring-forward test passes.
* [ ] Fall-back test passes.
* [ ] Ambiguous or nonexistent local-time behavior is documented and tested.

## Repository and Database

* [ ] Only the active schedule version is queried.
* [ ] Routing operations do not mutate schedule data.
* [ ] Phase 2 migrations remain valid.
* [ ] A clean database upgrades to head.
* [ ] Phase 2 fixtures can seed routing tests.

## Tests

* [ ] Routing unit tests pass.
* [ ] Routing integration tests pass.
* [ ] Property-based invariants pass.
* [ ] No test relies on network access.
* [ ] Synthetic fixtures are clearly labeled.
* [ ] Defect fixes include regression tests.

## Performance

* [ ] Direct routing benchmark meets the agreed target or has an accepted exception.
* [ ] Direct plus one-stop routing benchmark meets the agreed target or has an accepted exception.
* [ ] No uncontrolled N+1 query pattern exists.
* [ ] No unbounded graph traversal exists.

## Verification

* [ ] Formatting passes.
* [ ] Lint passes.
* [ ] Type checking passes.
* [ ] Backend unit tests pass.
* [ ] Backend integration tests pass.
* [ ] Property-based tests pass.
* [ ] Production builds pass.
* [ ] Docker Compose validates.
* [ ] PostgreSQL and Redis become healthy.
* [ ] Remote CI is green.

## Review

* [ ] No unresolved P0 finding exists within Phase 3 scope.
* [ ] No unresolved P1 finding exists within Phase 3 scope.
* [ ] `TASKS.md` reflects actual status.
* [ ] Working tree is clean.
* [ ] All Phase 3 changes are committed.
* [ ] Any required ADR has been accepted.

---

# Binary Release-Gate Rule

The final Phase 3 reviewer must return exactly one primary verdict:

* `PASS`
* `FAIL`

A `FAIL` may contain only reproducible blockers against this document.

The reviewer must not:

* Require a public search endpoint.
* Require airport autocomplete.
* Require a results page.
* Require exact GoWild taxes or fees.
* Require live availability.
* Require round-trip search.
* Require more than one connection.
* Require natural-language search.
* Require optional refactors.
* Treat future enhancements as Phase 3 blockers.

A `PASS` requires every mandatory completion-gate item to be satisfied or explicitly marked not applicable through an accepted ADR.

---

# Reviewer Reproduction Requirements

Every blocking finding must include:

* Exact file and location
* Exact failed command or test
* Expected behavior
* Actual behavior
* Relevant section of this document
* Smallest compliant correction

A reviewer must not block the phase using:

* Pure style preference
* Speculative future risk without reproduction
* An excluded future requirement
* A task status that contradicts this active-phase contract
* A proposed architectural rewrite when a bounded fix exists

---

# Scope Rule

The active phase is defined by this file.

The presence of partial future-phase code does not make that code part of Phase 3.

`TASKS.md` records implementation status but cannot expand the active phase.

The PRD and TDD define the complete product but do not make every future requirement part of the current phase.

When a future-phase implementation is incomplete and interferes with Phase 3, remove or isolate it rather than completing it.

---

# Phase 3 Exit Procedure

When the completion gate passes:

1. Confirm all remote CI checks are green.
2. Confirm `RTE-001` through `RTE-007` are marked `COMPLETE`.
3. Confirm later tasks remain factually marked.
4. Commit all final code and documentation changes. **Commit `PHASE.md` itself** so
   the phase tag captures the exact contract in force (the file is otherwise untracked).
5. Tag the repository. The completed-phase git tag is the durable record of each
   phase contract (the tagged commit's committed `PHASE.md` is that contract):

```bash
git add PHASE.md
git tag -a phase-3-complete -m "Phase 3 complete: deterministic routing engine (RTE-001 through RTE-007)"
git push origin phase-3-complete
```

6. Replace `PHASE.md` in place with the approved Phase 4 contract. This project does
   **not** archive prior contracts under `docs/phases/`; the `phase-N-complete` tag
   preserves each contract at the commit it governed. Recover an earlier contract with
   `git show phase-N-complete:PHASE.md` (valid for any phase whose `PHASE.md` was
   committed before tagging).
