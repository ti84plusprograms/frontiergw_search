# Frontier GoWild Destination Explorer

## Technical Design Document

**Document version:** 1.0
**Status:** Proposed
**Intended audience:** Software engineers, AI coding agents, technical leads, QA engineers, and DevOps engineers
**Related document:** Frontier GoWild Destination Explorer Product Requirements Document
**Primary objective:** Define an implementable architecture for discovering Frontier destinations reachable from an origin airport on a selected date, with estimated or verified GoWild pricing.

---

# 1. Purpose

This document defines the technical design for the Frontier GoWild Destination Explorer.

The system allows a user to select:

* An origin airport
* A departure date
* A maximum number of connections
* Optional price, timing, and duration constraints

The system returns:

* Direct and connecting Frontier itineraries
* Flight and layover details
* Estimated or verified GoWild pricing
* Availability status
* A link or handoff path to Frontier for booking

The system must treat route discovery, pricing, and inventory verification as separate concerns.

The application must remain useful even when verified GoWild inventory is unavailable.

---

# 2. Design Principles

## 2.1 Deterministic core

Flight routing, schedule filtering, connection validation, time calculations, and price calculations must be implemented using deterministic application logic.

A foundational model must not be used as the source of truth for:

* Routes
* Flight schedules
* Prices
* Taxes
* Availability
* Connection feasibility

---

## 2.2 Graceful degradation

The application must support multiple data-confidence levels.

A result may be:

1. **Scheduled**

   * The itinerary is theoretically possible from schedule data.
   * GoWild availability has not been checked.

2. **Estimated**

   * The route exists and the approximate GoWild cost has been calculated.

3. **Verified**

   * A permitted live data source confirmed GoWild availability and pricing.

4. **Stale**

   * The result was verified previously but is older than the configured freshness threshold.

5. **Unavailable**

   * The itinerary exists, but no GoWild fare is currently available.

6. **Unknown**

   * Verification failed or the data source returned an indeterminate result.

---

## 2.3 Data-source independence

The search engine must not depend directly on one specific schedule or availability provider.

External provider responses must be normalized into internal domain models.

The application should support replacing a data provider without rewriting the routing engine or frontend.

---

## 2.4 Low-cost MVP

The first version should operate using:

* A static or periodically updated Frontier route dataset
* A normalized airport database
* Deterministic route generation
* Estimated per-segment pricing
* No user account requirement
* No runtime LLM dependency

---

## 2.5 Legal and operational restraint

The production system must not depend on prohibited scraping or unauthorized automation.

Website automation must remain isolated behind a provider interface and disabled by default unless legal and contractual authorization is confirmed.

---

# 3. Scope

## 3.1 Included in initial implementation

* Airport search
* Departure-date selection
* Frontier route discovery
* Direct itinerary generation
* One-stop itinerary generation
* Timezone-aware calculations
* Connection validation
* Estimated GoWild pricing
* Result filtering
* Result sorting
* Search-result caching
* Frontier booking deep-link generation where feasible
* Provider abstraction for future live availability
* REST API
* Responsive web application
* Unit, integration, and end-to-end testing
* Deployment configuration
* Structured application logging

---

## 3.2 Deferred features

* Flight booking
* Payment processing
* Frontier credential storage
* Multi-airline support
* Native mobile applications
* Hotel booking
* Rental-car booking
* Push notifications
* Price alerts
* User profiles
* Saved trips
* Personalized recommendations
* Multi-city routing
* More than one connection
* Machine-learning ranking
* Automated Frontier website interaction
* International visa or entry-requirement analysis

---

# 4. Recommended Technology Stack

## 4.1 Frontend

* Next.js
* React
* TypeScript
* Tailwind CSS
* TanStack Query
* React Hook Form
* Zod
* Playwright for end-to-end testing
* Vitest or Jest for unit testing

---

## 4.2 Backend

Recommended:

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic
* PostgreSQL
* Redis for caching
* Pytest
* HTTPX for external API requests

Alternative:

* Next.js server routes with TypeScript
* Prisma or Drizzle ORM
* PostgreSQL

The Python backend is preferred because:

* Schedule transformation is naturally data-oriented.
* Graph-processing code is easy to express and test.
* Python has mature timezone, data-processing, and scientific libraries.
* It separates the frontend deployment lifecycle from the routing service.

---

## 4.3 Infrastructure

Initial deployment:

* Frontend: Vercel
* Backend: Railway, Render, Fly.io, or a container platform
* Database: Supabase PostgreSQL or managed PostgreSQL
* Cache: Managed Redis or Upstash
* Monitoring: Sentry plus structured logs
* CI/CD: GitHub Actions

Production-capable alternative:

* AWS ECS or Google Cloud Run
* Managed PostgreSQL
* Managed Redis
* Object storage for data imports
* Secret manager
* Centralized logging and tracing

---

# 5. High-Level Architecture

```text
┌────────────────────────────┐
│        Web Browser         │
│     Next.js Frontend       │
└─────────────┬──────────────┘
              │ HTTPS
              ▼
┌────────────────────────────┐
│        API Gateway         │
│       FastAPI Service      │
└───────┬─────────┬──────────┘
        │         │
        │         ├────────────────────────────┐
        │         │                            │
        ▼         ▼                            ▼
┌────────────┐ ┌───────────────┐     ┌──────────────────┐
│ PostgreSQL │ │ Redis Cache   │     │ Provider Adapters│
│            │ │               │     │                  │
│ Airports   │ │ Search cache  │     │ Schedule API     │
│ Routes     │ │ Availability  │     │ Availability API │
│ Flights    │ │ Rate limits   │     │ Static datasets  │
│ Snapshots  │ │               │     │                  │
└────────────┘ └───────────────┘     └────────┬─────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │ External Sources │
                                    └──────────────────┘
```

---

# 6. Logical Components

## 6.1 Frontend application

Responsibilities:

* Collect search criteria.
* Validate user input.
* Call backend search endpoints.
* Display results.
* Apply client-side sorting where appropriate.
* Display freshness and confidence labels.
* Generate booking handoff actions.
* Present errors and partial results clearly.

The frontend must not independently calculate prices or determine route feasibility.

---

## 6.2 Search API

Responsibilities:

* Validate incoming search parameters.
* Resolve the origin airport.
* Retrieve applicable schedule data.
* Generate direct and one-stop itineraries.
* Apply filters.
* Calculate estimated pricing.
* Enrich results with cached availability.
* Rank results.
* Return a stable response schema.

---

## 6.3 Schedule ingestion service

Responsibilities:

* Import route and flight schedule data.
* Validate airport codes.
* Normalize provider-specific fields.
* Resolve local times and timezones.
* Detect duplicates.
* Version schedule datasets.
* Record data provenance.
* Publish import metrics.

The ingestion service may run:

* On demand
* Daily
* Weekly
* Whenever a provider publishes updates

---

## 6.4 Availability provider interface

Responsibilities:

* Accept a normalized itinerary request.
* Query a permitted provider.
* Normalize the provider response.
* Return availability, price, currency, fees, and verification time.
* Distinguish provider failure from fare unavailability.

Availability verification must remain optional.

---

## 6.5 Pricing service

Responsibilities:

* Calculate estimated GoWild cost.
* Aggregate verified itinerary costs.
* Record whether pricing is estimated or verified.
* Avoid presenting estimates as guaranteed prices.

---

## 6.6 Airport metadata service

Responsibilities:

* Provide airport code, city, country, coordinates, and timezone.
* Support fuzzy airport search.
* Resolve metro areas where appropriate.
* Distinguish airports with similar city names.

---

## 6.7 Cache service

Responsibilities:

* Cache search results.
* Cache normalized provider responses.
* Avoid repeated live inventory queries.
* Store negative availability briefly.
* Invalidate results after configurable freshness windows.

---

# 7. Repository Structure

Recommended monorepo:

```text
gowild-explorer/
├── apps/
│   ├── web/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── public/
│   │   ├── tests/
│   │   └── package.json
│   │
│   └── api/
│       ├── app/
│       │   ├── api/
│       │   ├── core/
│       │   ├── db/
│       │   ├── domain/
│       │   ├── providers/
│       │   ├── repositories/
│       │   ├── schemas/
│       │   ├── services/
│       │   └── workers/
│       ├── migrations/
│       ├── tests/
│       ├── pyproject.toml
│       └── Dockerfile
│
├── packages/
│   ├── api-client/
│   ├── shared-types/
│   └── config/
│
├── data/
│   ├── seeds/
│   ├── imports/
│   └── samples/
│
├── docs/
│   ├── PRD.md
│   ├── TDD.md
│   ├── API.md
│   ├── DATA_SOURCES.md
│   └── RUNBOOK.md
│
├── infrastructure/
│   ├── docker-compose.yml
│   ├── terraform/
│   └── monitoring/
│
├── .github/
│   └── workflows/
│
├── Makefile
├── README.md
└── .env.example
```

---

# 8. Domain Model

## 8.1 Airport

```python
class Airport:
    code: str
    name: str
    city: str
    state_or_region: str | None
    country_code: str
    latitude: float
    longitude: float
    timezone: str
    is_active: bool
```

Requirements:

* `code` must be a valid three-letter IATA airport code.
* `timezone` must use an IANA timezone identifier.
* Airport codes must be stored in uppercase.

---

## 8.2 Route

Represents a known nonstop market operated by Frontier during an effective period.

```python
class Route:
    id: UUID
    origin_code: str
    destination_code: str
    effective_start: date
    effective_end: date | None
    operating_days: set[int]
    source_id: UUID
    is_active: bool
```

`operating_days` uses ISO weekday values:

* Monday: 1
* Tuesday: 2
* Wednesday: 3
* Thursday: 4
* Friday: 5
* Saturday: 6
* Sunday: 7

---

## 8.3 Scheduled flight

Represents a flight operating on one or more dates.

```python
class ScheduledFlight:
    id: UUID
    carrier_code: str
    flight_number: str
    origin_code: str
    destination_code: str
    departure_local_time: time
    arrival_local_time: time
    arrival_day_offset: int
    effective_start: date
    effective_end: date | None
    operating_days: set[int]
    equipment_code: str | None
    source_id: UUID
```

---

## 8.4 Flight instance

Represents a scheduled flight resolved for a specific operating date.

```python
class FlightInstance:
    scheduled_flight_id: UUID
    carrier_code: str
    flight_number: str
    origin_code: str
    destination_code: str
    departure_at: datetime
    arrival_at: datetime
    duration_minutes: int
```

All internal datetimes must be timezone-aware.

API responses should use ISO 8601 timestamps with offsets.

---

## 8.5 Itinerary segment

```python
class ItinerarySegment:
    sequence: int
    flight: FlightInstance
    estimated_price: Money | None
    verified_price: Money | None
    availability_status: AvailabilityStatus
```

---

## 8.6 Itinerary

```python
class Itinerary:
    id: str
    origin_code: str
    destination_code: str
    departure_at: datetime
    arrival_at: datetime
    segments: list[ItinerarySegment]
    connection_count: int
    total_duration_minutes: int
    airborne_duration_minutes: int
    total_layover_minutes: int
    price: PriceSummary
    availability: AvailabilitySummary
    booking_url: str | None
```

The itinerary ID must be deterministic for equivalent itinerary inputs.

Recommended derivation:

```text
SHA-256(
  departure_date +
  ordered carrier codes +
  ordered flight numbers +
  ordered origin/destination codes +
  ordered departure timestamps
)
```

---

## 8.7 Price summary

```python
class PriceSummary:
    amount: Decimal | None
    currency: str
    status: PriceStatus
    segment_count: int
    base_amount: Decimal | None
    taxes_and_fees: Decimal | None
    verified_at: datetime | None
    disclaimer: str
```

Price status values:

```text
ESTIMATED
VERIFIED
STALE
UNAVAILABLE
UNKNOWN
```

---

## 8.8 Availability summary

```python
class AvailabilitySummary:
    status: AvailabilityStatus
    checked_at: datetime | None
    source: str | None
    confidence: ConfidenceLevel
```

Availability status:

```text
NOT_CHECKED
AVAILABLE
UNAVAILABLE
UNKNOWN
STALE
```

Confidence level:

```text
LOW
MEDIUM
HIGH
```

---

# 9. Database Design

## 9.1 Tables

### airports

```sql
CREATE TABLE airports (
    code CHAR(3) PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    state_or_region TEXT,
    country_code CHAR(2) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    timezone TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### data_sources

```sql
CREATE TABLE data_sources (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    provider_type TEXT NOT NULL,
    version TEXT,
    retrieved_at TIMESTAMPTZ NOT NULL,
    effective_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    checksum TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### routes

```sql
CREATE TABLE routes (
    id UUID PRIMARY KEY,
    origin_code CHAR(3) NOT NULL REFERENCES airports(code),
    destination_code CHAR(3) NOT NULL REFERENCES airports(code),
    effective_start DATE NOT NULL,
    effective_end DATE,
    operating_days SMALLINT[] NOT NULL,
    source_id UUID NOT NULL REFERENCES data_sources(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT routes_no_self_loop
        CHECK (origin_code <> destination_code)
);
```

Recommended indexes:

```sql
CREATE INDEX idx_routes_origin_dates
ON routes(origin_code, effective_start, effective_end);

CREATE INDEX idx_routes_destination
ON routes(destination_code);
```

---

### scheduled_flights

```sql
CREATE TABLE scheduled_flights (
    id UUID PRIMARY KEY,
    carrier_code VARCHAR(3) NOT NULL DEFAULT 'F9',
    flight_number VARCHAR(8) NOT NULL,
    origin_code CHAR(3) NOT NULL REFERENCES airports(code),
    destination_code CHAR(3) NOT NULL REFERENCES airports(code),
    departure_local_time TIME NOT NULL,
    arrival_local_time TIME NOT NULL,
    arrival_day_offset SMALLINT NOT NULL DEFAULT 0,
    effective_start DATE NOT NULL,
    effective_end DATE,
    operating_days SMALLINT[] NOT NULL,
    equipment_code TEXT,
    source_id UUID NOT NULL REFERENCES data_sources(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT flights_no_self_loop
        CHECK (origin_code <> destination_code),
    CONSTRAINT valid_arrival_day_offset
        CHECK (arrival_day_offset BETWEEN 0 AND 2)
);
```

Recommended indexes:

```sql
CREATE INDEX idx_flights_origin_effective
ON scheduled_flights(origin_code, effective_start, effective_end);

CREATE INDEX idx_flights_destination
ON scheduled_flights(destination_code);

CREATE INDEX idx_flights_number
ON scheduled_flights(carrier_code, flight_number);
```

---

### availability_snapshots

```sql
CREATE TABLE availability_snapshots (
    id UUID PRIMARY KEY,
    itinerary_hash TEXT NOT NULL,
    origin_code CHAR(3) NOT NULL,
    destination_code CHAR(3) NOT NULL,
    departure_date DATE NOT NULL,
    segment_signature JSONB NOT NULL,
    status TEXT NOT NULL,
    total_amount NUMERIC(10, 2),
    base_amount NUMERIC(10, 2),
    taxes_and_fees NUMERIC(10, 2),
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    source_id UUID REFERENCES data_sources(id),
    checked_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    raw_reference JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Recommended indexes:

```sql
CREATE UNIQUE INDEX idx_availability_latest_unique
ON availability_snapshots(itinerary_hash, checked_at);

CREATE INDEX idx_availability_lookup
ON availability_snapshots(itinerary_hash, expires_at DESC);

CREATE INDEX idx_availability_route_date
ON availability_snapshots(origin_code, destination_code, departure_date);
```

---

### search_events

Optional analytics table:

```sql
CREATE TABLE search_events (
    id UUID PRIMARY KEY,
    anonymous_session_id TEXT,
    origin_code CHAR(3),
    departure_date DATE,
    filters JSONB NOT NULL,
    result_count INTEGER,
    duration_ms INTEGER,
    cache_hit BOOLEAN,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

No precise personal identifiers should be stored for anonymous users.

---

# 10. Search Request Model

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
  "include_unverified": true,
  "sort": "price"
}
```

---

# 11. Search Response Model

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
    "schedule_updated_at": "2026-08-01T04:00:00Z",
    "availability_checked_at": null
  },
  "result_count": 2,
  "results": [
    {
      "itinerary_id": "iti_1f8b...",
      "origin": "ATL",
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
        "amount": 14.91,
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
    "GoWild availability has not been verified."
  ]
}
```

---

# 12. Search Algorithm

## 12.1 Inputs

* Origin airport
* Departure date
* Maximum connections
* Minimum connection duration
* Maximum connection duration
* Optional time, duration, geography, and price filters

---

## 12.2 Direct itineraries

1. Query scheduled flights where:

   * `origin_code` equals the selected origin.
   * Selected date is within the effective date range.
   * Selected weekday is in `operating_days`.

2. Resolve each scheduled flight into a timezone-aware flight instance.

3. Reject invalid or incomplete schedule records.

4. Apply departure-time and destination filters.

5. Create one-segment itineraries.

---

## 12.3 One-stop itineraries

For each first segment:

1. Query flights departing from the first segment’s destination.
2. Resolve those flights for:

   * The same local date as arrival, or
   * The following date when the second departure occurs after midnight.
3. Calculate layover:

   * `second.departure_at - first.arrival_at`
4. Accept only when:

   * Layover is at least the configured minimum.
   * Layover does not exceed the configured maximum.
   * Final destination differs from the origin.
   * Final destination differs from the connection airport.
   * No repeated airport occurs.
   * Total duration remains within limits.
5. Create a two-segment itinerary.

---

## 12.4 Pseudocode

```python
def search_itineraries(criteria: SearchCriteria) -> list[Itinerary]:
    first_segments = schedule_repository.find_departures(
        origin=criteria.origin,
        operating_date=criteria.departure_date,
    )

    itineraries = []

    for first in resolve_instances(first_segments, criteria.departure_date):
        if not passes_first_segment_filters(first, criteria):
            continue

        itineraries.append(build_direct_itinerary(first))

        if criteria.max_connections < 1:
            continue

        candidate_dates = {
            first.arrival_at.date(),
            first.arrival_at.date() + timedelta(days=1),
        }

        second_segments = schedule_repository.find_departures_for_dates(
            origin=first.destination_code,
            operating_dates=candidate_dates,
        )

        for second in resolve_candidate_instances(second_segments):
            if not valid_connection(first, second, criteria):
                continue

            itinerary = build_one_stop_itinerary(first, second)

            if passes_itinerary_filters(itinerary, criteria):
                itineraries.append(itinerary)

    itineraries = deduplicate_itineraries(itineraries)
    itineraries = price_estimator.attach_estimates(itineraries)
    itineraries = availability_service.attach_cached_results(itineraries)
    itineraries = apply_final_filters(itineraries, criteria)
    itineraries = sort_itineraries(itineraries, criteria.sort)

    return itineraries
```

---

# 13. Timezone Handling

Timezone correctness is mandatory.

## 13.1 Rules

* Airport local times are stored as local wall-clock times plus airport timezone.
* Flight instances are constructed using the origin and destination IANA timezones.
* Arrival day offset must be applied before assigning destination timezone.
* Durations are calculated using UTC-normalized timestamps.
* API responses preserve local offsets.
* The frontend must not recalculate flight duration from displayed strings.

---

## 13.2 Example

ATL departure:

```text
2026-08-04 09:35 America/New_York
```

DEN arrival:

```text
2026-08-04 11:05 America/Denver
```

The apparent clock difference is 90 minutes, but the actual elapsed duration is 210 minutes.

The backend must calculate the duration from timezone-aware timestamps.

---

## 13.3 Daylight-saving transitions

Tests must cover:

* Spring-forward dates
* Fall-back dates
* Airports in regions without daylight-saving changes
* International timezone differences
* Flights arriving after midnight

---

# 14. Connection Validation

Default configuration:

```text
Minimum connection: 45 minutes
Maximum connection: 4 hours
Maximum overnight connection: disabled
Maximum total duration: 12 hours
Maximum connections: 1
```

An itinerary is invalid when:

* The second flight departs before the first flight arrives.
* The connection is shorter than the minimum.
* The connection exceeds the maximum.
* The itinerary returns to the origin.
* The same flight is duplicated.
* The destination airport appears earlier in the path.
* The computed duration is negative.
* A schedule record has invalid timezone data.
* Total travel duration exceeds the selected maximum.

Airport-specific minimum-connection-time rules may be introduced later.

---

# 15. Price Estimation

## 15.1 Initial estimator

The MVP uses a configurable estimated per-segment amount.

Example environment configuration:

```text
DOMESTIC_ESTIMATED_SEGMENT_PRICE_USD=14.91
INTERNATIONAL_ESTIMATION_ENABLED=false
```

Estimated itinerary price:

```text
estimated total = segment count × configured estimated segment amount
```

The system must not use floating-point arithmetic for money.

Use:

* Python `Decimal`
* PostgreSQL `NUMERIC`
* Integer cents where appropriate

---

## 15.2 Estimate labeling

Every estimated price must include:

* Status: `ESTIMATED`
* Segment count
* Currency
* Disclaimer
* No “live” or “guaranteed” label

---

## 15.3 Verified pricing

When an authorized provider is available:

```python
class AvailabilityProvider(Protocol):
    async def check_itinerary(
        self,
        itinerary: Itinerary,
        context: AvailabilityContext,
    ) -> AvailabilityResult:
        ...
```

Expected result:

```python
class AvailabilityResult:
    status: AvailabilityStatus
    total_amount: Decimal | None
    base_amount: Decimal | None
    taxes_and_fees: Decimal | None
    currency: str
    checked_at: datetime
    expires_at: datetime
    provider_reference: str | None
    raw_metadata: dict
```

---

# 16. Provider Adapter Design

## 16.1 Schedule provider interface

```python
class ScheduleProvider(Protocol):
    async def fetch_schedule(
        self,
        start_date: date,
        end_date: date,
    ) -> ScheduleImportBatch:
        ...
```

Implementations may include:

* Static CSV provider
* Static JSON provider
* Authorized commercial API provider
* Official airline provider

---

## 16.2 Normalization layer

External fields must be transformed into internal models before persistence.

Provider-specific fields must not leak into:

* Search services
* API responses
* Frontend types
* Pricing services

---

## 16.3 Provider resilience

Each adapter must implement:

* Connection timeout
* Read timeout
* Retries with exponential backoff
* Response validation
* Provider-specific error mapping
* Rate-limit awareness
* Structured logging
* Circuit-breaking where appropriate

---

## 16.4 Browser automation adapter

Any browser automation implementation must:

* Be stored in a separate module.
* Be disabled by default.
* Require an explicit feature flag.
* Never store plaintext Frontier credentials.
* Never be enabled in production without authorization.
* Be excluded from core search functionality.

Suggested feature flag:

```text
ENABLE_FRONTIER_BROWSER_AUTOMATION=false
```

---

# 17. Caching Strategy

## 17.1 Search cache

Key:

```text
search:v1:{origin}:{date}:{normalized_filters_hash}
```

Recommended TTL:

* Schedule-only result: 1–6 hours
* Future-date result: up to 12 hours
* Same-day search: 5–30 minutes
* Live verified result: provider-specific, generally 1–10 minutes

---

## 17.2 Availability cache

Key:

```text
availability:v1:{itinerary_hash}
```

Suggested TTLs:

* Available fare: 2–5 minutes
* Unavailable fare: 1–3 minutes
* Provider error: 30–60 seconds
* Static estimate: 24 hours

---

## 17.3 Cache invalidation

Invalidate search caches when:

* A schedule import succeeds.
* Airport metadata changes.
* Pricing configuration changes.
* Routing algorithm version changes.
* A critical defect is fixed.

Include algorithm and schema versions in cache keys.

---

# 18. REST API Design

Base path:

```text
/api/v1
```

---

## 18.1 Health endpoint

```http
GET /api/v1/health
```

Response:

```json
{
  "status": "ok",
  "database": "ok",
  "cache": "ok",
  "schedule_version": "2026-08-01"
}
```

---

## 18.2 Airport search

```http
GET /api/v1/airports?query=atl&limit=10
```

Response:

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
  ]
}
```

---

## 18.3 Destination search

```http
POST /api/v1/search
Content-Type: application/json
```

Request:

```json
{
  "origin": "ATL",
  "departure_date": "2026-08-04",
  "max_connections": 1,
  "min_connection_minutes": 45,
  "max_connection_minutes": 240,
  "max_total_duration_minutes": 720,
  "include_unverified": true,
  "sort": "price"
}
```

Response: `SearchResponse`

---

## 18.4 Itinerary availability check

```http
POST /api/v1/availability/check
```

Request:

```json
{
  "itinerary_id": "iti_1f8b..."
}
```

Behavior:

* Retrieve the itinerary from signed or stored search context.
* Reject arbitrary client-constructed itinerary data.
* Query an authorized provider.
* Cache the result.
* Return verified availability.

---

## 18.5 Schedule metadata

```http
GET /api/v1/schedules/status
```

Response:

```json
{
  "source": "static-frontier-schedule",
  "version": "2026-08-01",
  "retrieved_at": "2026-08-01T04:00:00Z",
  "effective_start": "2026-08-01",
  "effective_end": "2026-10-31",
  "flight_count": 1830
}
```

---

## 18.6 OpenAPI

FastAPI must expose:

```text
/docs
/openapi.json
```

The OpenAPI specification must be checked into the repository for agent and frontend consumption.

---

# 19. Validation Rules

## 19.1 Search request

* Origin must be exactly three alphabetical characters.
* Origin must exist and be active.
* Departure date must be within the supported schedule range.
* Maximum connections must be `0` or `1`.
* Minimum connection must be between 20 and 360 minutes.
* Maximum connection must be greater than the minimum.
* Maximum total duration must be between 60 and 1,440 minutes.
* Maximum price must be nonnegative.
* `domestic_only` and `international_only` cannot both be true.
* Time filters must use 24-hour local-time format.

---

## 19.2 Provider data

Reject or quarantine records with:

* Unknown airport codes
* Missing flight numbers
* Invalid operating weekdays
* Arrival day offset outside accepted bounds
* Effective end before effective start
* Malformed local times
* Duplicate provider identifiers with contradictory values

---

# 20. Frontend Design

## 20.1 Routes

```text
/
  Search page

/results
  Search results

/about
  Product and pricing disclaimers

/data-status
  Schedule freshness and source information
```

Search state may initially be represented in URL query parameters.

Example:

```text
/results?origin=ATL&date=2026-08-04&connections=1&sort=price
```

This enables:

* Shareable searches
* Browser navigation
* Refresh persistence
* Basic analytics

---

## 20.2 Main components

```text
AirportCombobox
DepartureDatePicker
SearchFilters
SearchSummary
ResultsToolbar
ItineraryCard
SegmentTimeline
PriceBadge
AvailabilityBadge
FreshnessIndicator
EmptyState
ErrorState
LoadingSkeleton
DestinationMap
```

The map is optional for MVP.

---

## 20.3 Itinerary card requirements

Each result card must show:

* Destination city
* Destination airport code
* Local departure time
* Local arrival time
* Total duration
* Number of connections
* Connection airport and layover
* Segment flight numbers
* Estimated or verified price
* Availability status
* Data freshness
* Booking handoff action

---

## 20.4 Accessibility

The frontend must meet WCAG 2.1 AA where practicable.

Requirements:

* Full keyboard navigation
* Semantic labels
* Accessible combobox behavior
* Visible focus states
* Sufficient contrast
* Screen-reader-friendly itinerary structure
* No color-only availability indicators
* Touch targets at least 44 by 44 CSS pixels
* Loading states announced appropriately

---

# 21. Booking Handoff

The application does not book flights.

Potential behavior:

1. Generate a permitted Frontier search URL when stable parameters are known.
2. Open Frontier in a new tab.
3. Display the exact search parameters the user must enter when deep linking is unavailable.
4. Never claim that the displayed result remains bookable.
5. Show a final-price disclaimer.

Example action label:

```text
Check on Frontier
```

Avoid:

```text
Book for $14.91
```

unless the fare is verified and the action genuinely preserves that offer.

---

# 22. Natural-Language Search

Natural-language search is optional and isolated from the core.

## 22.1 Input

```text
Show direct flights somewhere warm under $40 after 6 p.m.
```

## 22.2 Output schema

```json
{
  "max_connections": 0,
  "max_price": 40,
  "depart_after": "18:00",
  "destination_preferences": {
    "climate": "warm"
  }
}
```

## 22.3 Model responsibilities

Allowed:

* Convert free-form input into structured filters.
* Explain why results match preferences.
* Summarize destination information.

Not allowed:

* Invent schedule data.
* Invent pricing.
* Mark a route available.
* Override backend validation.
* Execute arbitrary backend queries.

---

## 22.4 Tool contract

The model must call a typed search tool.

```json
{
  "name": "search_destinations",
  "description": "Search deterministic Frontier itinerary data.",
  "parameters": {
    "type": "object",
    "properties": {
      "origin": {
        "type": "string"
      },
      "departure_date": {
        "type": "string",
        "format": "date"
      },
      "max_connections": {
        "type": "integer",
        "minimum": 0,
        "maximum": 1
      },
      "max_price": {
        "type": ["number", "null"]
      }
    },
    "required": [
      "origin",
      "departure_date"
    ]
  }
}
```

---

# 23. Security Design

## 23.1 General controls

* HTTPS only
* Strict input validation
* Parameterized queries
* Content Security Policy
* Secure HTTP headers
* Rate limiting
* Dependency scanning
* Secret scanning
* Environment-based secret management
* No secrets in frontend bundles
* No plaintext credential storage
* Minimal database privileges

---

## 23.2 Authentication

User authentication is not required for MVP.

Administrative endpoints must require authentication.

Examples:

* Trigger schedule import
* View provider diagnostics
* Modify pricing configuration
* Clear caches

---

## 23.3 Rate limiting

Suggested anonymous limits:

```text
Airport search: 120 requests per minute per IP
Destination search: 30 requests per minute per IP
Live availability check: 5 requests per minute per IP
```

Limits should be configurable.

---

## 23.4 Signed itinerary references

The availability endpoint must not trust arbitrary flight data submitted by clients.

Approaches:

* Store search results temporarily using a search ID.
* Return signed itinerary tokens.
* Reconstruct the itinerary from server-side schedule data.

Recommended signed token payload:

```json
{
  "itinerary_hash": "abc123",
  "search_id": "uuid",
  "expires_at": 1785800000
}
```

---

## 23.5 Privacy

Do not store:

* Frontier account passwords
* Passport details
* Payment details
* Precise user location unless explicitly required
* Search history tied to identity without consent

Anonymous analytics must use rotating or non-identifying session IDs.

---

# 24. Error Model

All API errors use a consistent schema.

```json
{
  "error": {
    "code": "INVALID_DEPARTURE_DATE",
    "message": "The departure date is outside the available schedule range.",
    "details": {
      "supported_start": "2026-08-01",
      "supported_end": "2026-10-31"
    },
    "request_id": "req_123"
  }
}
```

---

## 24.1 Error codes

```text
INVALID_REQUEST
INVALID_AIRPORT
INVALID_DEPARTURE_DATE
DATE_OUTSIDE_SCHEDULE_RANGE
NO_SCHEDULE_DATA
NO_ITINERARIES
PROVIDER_UNAVAILABLE
AVAILABILITY_UNKNOWN
RATE_LIMITED
DATABASE_UNAVAILABLE
CACHE_UNAVAILABLE
INTERNAL_ERROR
```

---

## 24.2 Partial failure

If schedule search succeeds but live verification fails:

* Return schedule results.
* Mark availability as `UNKNOWN`.
* Include a warning.
* Do not fail the entire request.

---

# 25. Observability

## 25.1 Structured logs

Every request log should include:

* Request ID
* Route
* Status code
* Duration
* Cache hit or miss
* Result count
* Origin
* Departure date
* Provider calls
* Provider latency
* Error code

Avoid logging sensitive data.

---

## 25.2 Metrics

Required metrics:

```text
http_requests_total
http_request_duration_ms
search_requests_total
search_duration_ms
search_results_count
search_cache_hit_ratio
schedule_records_loaded
schedule_import_failures
availability_checks_total
availability_provider_latency_ms
availability_provider_errors
database_query_duration_ms
```

---

## 25.3 Tracing

Distributed tracing is optional for MVP.

Add tracing when:

* Multiple provider integrations exist.
* Background jobs become significant.
* Search requests involve several services.
* Provider latency becomes difficult to diagnose.

---

## 25.4 Alerts

Alert on:

* API error rate above threshold
* Search latency degradation
* Schedule dataset expiration
* Failed schedule imports
* Database connectivity failure
* Provider error spikes
* Zero-result spikes from major airports
* Cache outage

---

# 26. Testing Strategy

## 26.1 Unit tests

Backend:

* Airport validation
* Weekday matching
* Effective-date filtering
* Flight-instance construction
* Timezone conversion
* Arrival day offset
* Direct itinerary generation
* One-stop generation
* Connection validation
* Loop prevention
* Duration calculations
* Price estimation
* Deduplication
* Sorting
* Cache-key generation
* Provider response normalization

Frontend:

* Search-form validation
* Filter serialization
* Price-label rendering
* Availability-label rendering
* Itinerary timeline rendering
* Empty and error states

---

## 26.2 Integration tests

* API with test PostgreSQL
* API with Redis
* Schedule import pipeline
* Provider adapter using mocked upstream responses
* Search endpoint with seeded schedules
* Availability snapshot retrieval
* Cache invalidation after data import
* OpenAPI schema validation

---

## 26.3 End-to-end tests

Example scenarios:

1. Search ATL for a date with direct results.
2. Search ATL with one-stop itineraries enabled.
3. Apply direct-only filter.
4. Sort by lowest estimated price.
5. Search an invalid airport.
6. Search outside schedule range.
7. Simulate provider failure.
8. Open a shareable search URL.
9. Verify mobile layout.
10. Verify keyboard-only search.

---

## 26.4 Property-based testing

Use property-based tests for routing invariants.

Examples:

* Arrival must be after departure.
* Total duration must be nonnegative.
* No itinerary may repeat the origin.
* Segment ordering must be chronological.
* Connection count equals segment count minus one.
* Estimated price must increase monotonically with segment count under a fixed estimator.

---

## 26.5 Performance tests

Initial targets:

* Airport lookup p95: under 150 ms
* Schedule-only search p95: under 750 ms
* Cached search p95: under 200 ms
* Search result generation for a major hub: under 1 second
* Support at least 20 concurrent searches on initial infrastructure

Use Locust, k6, or an equivalent load-testing tool.

---

# 27. CI/CD Pipeline

## 27.1 Pull-request checks

Frontend:

* Type check
* Lint
* Unit tests
* Build
* Accessibility smoke test

Backend:

* Format check
* Lint
* Type check
* Unit tests
* Integration tests
* Migration validation
* OpenAPI diff check

Security:

* Dependency audit
* Secret scan
* Container vulnerability scan

---

## 27.2 Deployment stages

```text
Local
↓
Preview
↓
Staging
↓
Production
```

Production deployment must require:

* Passing tests
* Successful migration dry run
* No critical security findings
* Staging smoke tests
* Manual approval initially

---

# 28. Database Migration Strategy

* Use Alembic.
* Never edit an applied production migration.
* Every schema change requires a forward migration.
* Destructive changes require a two-stage deployment.
* Imports must remain backward-compatible during rolling deployments.
* Production backups must be verified before major migrations.

---

# 29. Background Jobs

Potential jobs:

```text
schedule_import
schedule_validation
schedule_expiration_check
availability_snapshot_cleanup
search_analytics_rollup
cache_warmup
```

Initial scheduler options:

* Platform cron
* GitHub Actions for low-frequency imports
* Celery or Dramatiq later
* Managed job service

Do not introduce a dedicated worker queue until operational need justifies it.

---

# 30. Schedule Import Pipeline

## 30.1 Pipeline

```text
Fetch
↓
Store raw source
↓
Validate file or response
↓
Normalize records
↓
Resolve airports
↓
Detect duplicates
↓
Run quality checks
↓
Write new source version
↓
Activate new dataset
↓
Invalidate search cache
↓
Publish metrics
```

---

## 30.2 Atomic activation

A schedule import must not partially replace active data.

Recommended process:

1. Load data into staging tables.
2. Validate counts and integrity.
3. Create a new `data_source` version.
4. Mark the previous version inactive.
5. Activate the new version in one transaction.
6. Invalidate relevant caches.

---

## 30.3 Data-quality checks

* Every airport exists.
* Every origin differs from destination.
* Every flight has at least one operating day.
* No invalid effective-date range.
* No impossible local time.
* No excessive duplicate rate.
* Flight count is within expected bounds.
* Major known hubs do not unexpectedly return zero departures.
* Data has a supported effective range.

---

# 31. Feature Flags

Recommended flags:

```text
ENABLE_ONE_STOP_SEARCH=true
ENABLE_LIVE_AVAILABILITY=false
ENABLE_NATURAL_LANGUAGE_SEARCH=false
ENABLE_DESTINATION_MAP=false
ENABLE_FRONTIER_BROWSER_AUTOMATION=false
ENABLE_SEARCH_ANALYTICS=true
ENABLE_INTERNATIONAL_ESTIMATES=false
```

Feature flags must be evaluated server-side for protected functionality.

---

# 32. Configuration

Example environment variables:

```text
APP_ENV=development
DATABASE_URL=
REDIS_URL=
API_BASE_URL=
FRONTEND_URL=

DEFAULT_MIN_CONNECTION_MINUTES=45
DEFAULT_MAX_CONNECTION_MINUTES=240
DEFAULT_MAX_TOTAL_DURATION_MINUTES=720

DOMESTIC_ESTIMATED_SEGMENT_PRICE_USD=14.91
INTERNATIONAL_ESTIMATION_ENABLED=false

SEARCH_CACHE_TTL_SECONDS=3600
AVAILABILITY_CACHE_TTL_SECONDS=180

ENABLE_ONE_STOP_SEARCH=true
ENABLE_LIVE_AVAILABILITY=false
ENABLE_NATURAL_LANGUAGE_SEARCH=false
ENABLE_FRONTIER_BROWSER_AUTOMATION=false

SENTRY_DSN=
LOG_LEVEL=INFO
```

---

# 33. Implementation Phases

## Phase 1: Foundation

Deliverables:

* Monorepo
* Local Docker environment
* PostgreSQL schema
* Airport seed data
* Health endpoint
* CI checks
* Basic frontend shell

Acceptance criteria:

* Frontend and backend run locally.
* Database migrations succeed.
* Health endpoint reports status.
* Airport autocomplete works.

---

## Phase 2: Schedule ingestion

Deliverables:

* Static provider adapter
* Schedule normalization
* Import command
* Data validation
* Schedule status endpoint

Acceptance criteria:

* A versioned schedule dataset can be imported.
* Invalid rows are rejected or quarantined.
* Import is atomic.
* Active schedule metadata is queryable.

---

## Phase 3: Direct search

Deliverables:

* Search request schema
* Direct-flight query
* Timezone-aware flight instances
* Estimated pricing
* Results page

Acceptance criteria:

* User can search an origin and date.
* Direct destinations appear.
* Durations are correct.
* Every price is labeled estimated.
* Results return in under one second under expected load.

---

## Phase 4: One-stop search

Deliverables:

* Connection generation
* Layover validation
* Loop prevention
* Duration filters
* Connection UI

Acceptance criteria:

* Valid one-stop itineraries are returned.
* Invalid and circular routes are excluded.
* Overnight and timezone edge cases are tested.

---

## Phase 5: Caching and hardening

Deliverables:

* Redis integration
* Search caching
* Rate limiting
* Structured logs
* Monitoring
* Error standardization

Acceptance criteria:

* Repeat searches use cache.
* Cache failures do not make search unavailable.
* Errors include request IDs.
* Basic dashboards and alerts exist.

---

## Phase 6: Availability-provider integration

Deliverables:

* Provider interface
* Authorized provider adapter
* Availability endpoint
* Snapshot persistence
* Freshness indicators

Acceptance criteria:

* Verified prices are clearly distinguished.
* Provider failure degrades to schedule-only results.
* Repeated checks respect TTL and rate limits.

---

## Phase 7: Natural-language search

Deliverables:

* Typed tool schema
* Intent parser
* Structured-filter validation
* AI-generated result explanations

Acceptance criteria:

* Model output is validated before search.
* No model-generated routes or prices appear.
* Search remains functional when the model is unavailable.

---

# 34. Agent Work Packages

Each work package should be implemented on a separate branch or worktree.

## Agent A: Repository and infrastructure

Tasks:

* Initialize monorepo.
* Configure frontend and backend.
* Add Docker Compose.
* Add PostgreSQL and Redis.
* Add CI workflows.
* Create environment templates.
* Write local setup documentation.

Dependencies:

* None

Deliverables:

* Running development environment
* CI pipeline
* Root README

---

## Agent B: Database and ingestion

Tasks:

* Implement SQLAlchemy models.
* Create Alembic migrations.
* Add airport seeding.
* Define provider interfaces.
* Implement static CSV or JSON provider.
* Implement atomic schedule imports.
* Add data-quality checks.

Dependencies:

* Agent A foundation

Deliverables:

* Database schema
* Import command
* Seed datasets
* Import tests

---

## Agent C: Routing engine

Tasks:

* Implement schedule repository.
* Resolve scheduled flights into flight instances.
* Implement direct search.
* Implement one-stop search.
* Validate connections.
* Deduplicate itineraries.
* Add sorting and filtering.
* Write unit and property-based tests.

Dependencies:

* Domain models
* Database repository interface

Deliverables:

* Routing service
* Search algorithm
* Comprehensive tests

---

## Agent D: API service

Tasks:

* Implement request and response schemas.
* Add airport endpoint.
* Add search endpoint.
* Add schedule-status endpoint.
* Add error middleware.
* Add request IDs.
* Generate OpenAPI specification.

Dependencies:

* Agents B and C

Deliverables:

* FastAPI application
* OpenAPI contract
* Integration tests

---

## Agent E: Frontend

Tasks:

* Build search page.
* Implement airport autocomplete.
* Implement date picker.
* Build results list.
* Build itinerary cards.
* Add filters and sorting.
* Add URL state.
* Add responsive and accessible behavior.

Dependencies:

* API contract from Agent D

Deliverables:

* Next.js application
* Component tests
* End-to-end tests

---

## Agent F: Pricing and availability

Tasks:

* Implement estimated price service.
* Define availability provider interface.
* Implement snapshot storage.
* Implement freshness logic.
* Implement availability endpoint.
* Add mocked provider for development.

Dependencies:

* Agents B, C, and D

Deliverables:

* Pricing module
* Availability module
* Mock provider
* Integration tests

---

## Agent G: Observability and security

Tasks:

* Add structured logging.
* Add metrics.
* Add Sentry.
* Add rate limiting.
* Add security headers.
* Add dependency and secret scanning.
* Create operational runbook.

Dependencies:

* API and frontend foundations

Deliverables:

* Monitoring configuration
* Security controls
* Runbook

---

## Agent H: QA and release validation

Tasks:

* Build end-to-end test suite.
* Add performance tests.
* Test timezone edge cases.
* Validate accessibility.
* Validate deployment.
* Produce release checklist.

Dependencies:

* All implementation agents

Deliverables:

* QA report
* Load-test report
* Release approval checklist

---

# 35. Agent Coordination Rules

All agents must follow these rules:

1. Do not modify shared interfaces without updating the relevant contract.
2. Do not introduce a new dependency without documenting why it is necessary.
3. Do not change database tables without a migration.
4. Do not expose provider-specific fields through public APIs.
5. Do not use an LLM for deterministic route calculations.
6. Do not present estimates as verified prices.
7. Do not store Frontier credentials.
8. Add tests for every defect fixed.
9. Keep commits scoped to one concern.
10. Update documentation when behavior changes.
11. Run formatters, linters, type checks, and tests before handoff.
12. Document any unresolved assumptions in the pull request.

---

# 36. Definition of Done

A feature is complete only when:

* Functional requirements are implemented.
* Input validation exists.
* Unit tests exist.
* Integration tests exist where applicable.
* Error states are handled.
* Logs and metrics are present where relevant.
* Documentation is updated.
* Accessibility has been considered.
* Security implications have been reviewed.
* CI passes.
* No critical or high-severity dependency issues remain.
* Acceptance criteria are demonstrably satisfied.

---

# 37. MVP Acceptance Criteria

The MVP is ready when a user can:

1. Open the application on desktop or mobile.
2. Search for an airport by city or code.
3. Select a supported departure date.
4. Search direct and one-stop Frontier itineraries.
5. Filter by connections, departure time, duration, and estimated cost.
6. Sort results.
7. See correct timezone-aware departure and arrival information.
8. See estimated GoWild pricing per itinerary.
9. Clearly understand that pricing and availability are not guaranteed.
10. Open Frontier to verify and complete booking.

Technical criteria:

* Search p95 is below one second under initial load expectations.
* No valid result contains a chronological or circular-routing defect.
* Schedule imports are versioned and atomic.
* The application remains usable if Redis is unavailable.
* The application remains usable if a live provider is unavailable.
* Backend test coverage is concentrated on routing, timing, and pricing logic.
* Critical workflows are covered by end-to-end tests.

---

# 38. Known Risks

## Data availability risk

The system may not receive authorized GoWild inventory.

Mitigation:

* Keep schedule discovery useful independently.
* Clearly label all estimates.
* Preserve provider abstraction.

---

## Schedule accuracy risk

Static route data may not reflect cancellations or seasonal changes.

Mitigation:

* Version data.
* Show freshness.
* Refresh regularly.
* Distinguish scheduled from verified.

---

## Pricing risk

Per-segment estimates may differ from final taxes and fees.

Mitigation:

* Use disclaimers.
* Never label estimates as live.
* Add verified provider data when available.

---

## Timezone risk

Incorrect timezone logic can produce invalid connections.

Mitigation:

* Use IANA timezones.
* Store timezone-aware timestamps.
* Add extensive edge-case tests.

---

## Provider lock-in risk

A third-party API may change terms or pricing.

Mitigation:

* Use provider interfaces.
* Normalize data.
* Avoid provider-specific logic in domain services.

---

## Legal risk

Unauthorized browser automation may violate terms or agreements.

Mitigation:

* Disable automation by default.
* Require authorization before production use.
* Keep automation outside the core system.

---

## Search explosion risk

Adding multiple stops, round trips, or large date ranges can increase computational complexity.

Mitigation:

* Limit MVP to one connection.
* Use indexed queries.
* Enforce duration and connection bounds.
* Cache results.
* Add asynchronous search only if needed later.

---

# 39. Future Architecture Extensions

Potential future services:

```text
Recommendation Service
Weather Service
Hotel Price Service
Alert Service
User Profile Service
Trip Scoring Service
Notification Service
Historical Availability Service
```

Possible future capabilities:

* Round-trip compatibility search
* Multi-day flexible date search
* Destination weather
* Hotel-cost ranking
* Fare-history analytics
* Personalized destination ranking
* Email or push alerts
* Saved searches
* Native mobile clients
* Multi-airline pass support

These extensions should consume the normalized itinerary API rather than bypass the routing service.

---

# 40. Final Technical Recommendation

Build the system in this order:

1. Airport and schedule data model
2. Atomic schedule ingestion
3. Direct deterministic routing
4. Timezone correctness
5. One-stop deterministic routing
6. Estimated pricing
7. Responsive frontend
8. Caching and monitoring
9. Authorized availability integration
10. Natural-language interaction

Do not begin with AI agents, browser automation, or live Frontier account integration.

The principal engineering asset is the normalized, deterministic route and itinerary engine. All AI, recommendation, weather, hotel, and alert capabilities should be layered on top of that foundation.