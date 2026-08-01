Use:

# Architecture Decision Log

Only approved decisions belong in this file.

## Decision template

### ADR-XXX: Title

**Status:** Proposed | Accepted | Rejected | Superseded  
**Date:** YYYY-MM-DD  
**Context:**  
**Decision:**  
**Consequences:**  
**PRD/TDD sections affected:**  
**Approved by:**  

---

## ADR-001: Initial technology stack

**Status:** Accepted  
**Date:** 2026-07-31  
**Context:** The project requires a web frontend, deterministic routing backend, relational storage, and optional caching.  
**Decision:** Use Next.js and TypeScript for the frontend, FastAPI and Python for the backend, PostgreSQL for persistence, and Redis for optional caching.  
**Consequences:** The project uses a monorepo with separately deployable frontend and backend applications.  
**PRD/TDD sections affected:** TDD Sections 4 and 7  
**Approved by:** Project owner

Use this file whenever either agent proposes deviating from the TDD.

---

## ADR-002: Monorepo tooling, package manager, and Python build tool

**Status:** Accepted
**Date:** 2026-07-31
**Context:** TDD Section 7 specifies a monorepo directory layout (`apps/web`, `apps/api`, `packages/*`) but does not name a workspace tool, JavaScript package manager, or Python dependency/build tool. FND-001 (initialize monorepo), FND-003 (configure FastAPI), and FND-004 (configure Next.js) cannot proceed without these choices. The audit of PRD/TDD readiness flagged this as a blocking gap for Phase 1.
**Decision:**
- Use native `pnpm` workspaces (via root `pnpm-workspace.yaml`) for the JavaScript/TypeScript side. No additional build orchestrator (Turborepo/Nx) is introduced in Phase 1; add one later only if cross-package build orchestration becomes a real pain point.
- Use `pnpm` as the package manager. It is already installed in the target environment, supports workspaces natively, and avoids adding a new dependency.
- Use plain `pip` with a `venv` and a standard `pyproject.toml` (PEP 621 metadata, setuptools backend) for the Python backend. Neither Poetry nor uv is installed in the environment and installing one would add an unnecessary new dependency (CLAUDE.md: "Do not add dependencies unless necessary and documented"). Revisit if the team standardizes on one later.
- Use GitHub Actions for CI, matching the existing GitHub remote and TDD §4.3/§27 assumption.
**Consequences:** Root `package.json` + `pnpm-workspace.yaml` define the JS workspace containing `apps/web` (and `packages/*` once populated in later phases). `apps/api` is a self-contained Python project with its own `pyproject.toml`, `venv`, and `requirements`-less dependency list declared in `pyproject.toml`. CI installs both toolchains independently.
**PRD/TDD sections affected:** TDD Section 7 (repository structure), Section 4 (technology stack)
**Approved by:** Project owner (via delegated implementation instruction to proceed with foundation PR)

---

## ADR-003: DST-ambiguous and nonexistent local flight times are rejected

**Status:** Accepted
**Date:** 2026-07-31
**Context:** Phase 3 resolves schedule definitions (tz-naive local wall-clock `departure_local_time` / `arrival_local_time`) into timezone-aware `FlightInstance` datetimes using the origin/destination airport IANA timezones (`PHASE.md` §Timezone Awareness, §Flight-Instance Resolution). On daylight-saving transition days a local wall-clock time can be **nonexistent** (spring-forward gap) or **ambiguous** (fall-back fold). `PHASE.md` §Daylight-Saving-Time Tests requires the implementation to define how these are handled and states that any alternative to the recommended rule requires an accepted ADR.
**Decision:** When combining a service date with a local time in an airport's `ZoneInfo` produces a **nonexistent** or **ambiguous** instant, the routing engine **rejects that flight instance** (it does not produce an itinerary from it) and records it as an invalid/quarantined resolution with a diagnostic. Detection uses stdlib `zoneinfo` fold semantics: an instant is nonexistent when normalizing through UTC and back does not reproduce the original wall-clock time; ambiguous when `fold=0` and `fold=1` map to different UTC instants. The engine does not silently guess an offset. A future source that supplies an explicit UTC offset (enabling deterministic resolution) may relax this, but only via a superseding ADR with explicit tests.
**Consequences:** Deterministic, safe behavior on DST edges; a small number of transition-day flights whose scheduled local time falls in a gap/fold will not appear in results rather than appearing at a guessed time. Requires explicit spring-forward and fall-back tests (already mandated by `PHASE.md`). No floating-point or naive datetime arithmetic is used.
**PRD/TDD sections affected:** TDD §13.3 (daylight-saving transitions); PHASE.md (Phase 3) §Timezone Awareness, §Daylight-Saving-Time Tests
**Approved by:** Project owner (delegated instruction to proceed with Phase 3)

---

## ADR-004: Deduplication conflict-precedence rule

**Status:** Accepted
**Date:** 2026-07-31
**Context:** `PHASE.md` §11–§12 require every itinerary to carry a deterministic SHA-256 identity derived from a canonical segment signature, and require the engine to collapse equivalent duplicates without arbitrary silent selection. Duplicate candidates with the **same** itinerary identity may still carry differing non-identity metadata (e.g. `scheduled_flight_id`, `equipment_code`, source row) arising from reimported/overlapping schedule records. §12 requires a documented precedence rule, outright rejection, or a diagnostic — not arbitrary selection.
**Decision:** Itinerary identity is the SHA-256 of the canonical signature over ordered (operating date, carrier codes, flight numbers, origin/destination codes, UTC-normalized departure and arrival instants). Two itineraries with the **same** identity are duplicates. On collapse, the engine keeps a single **deterministic winner** chosen by a total order on non-identity fields: (1) lexicographically smallest tuple of segment `scheduled_flight_id` values, then (2) smallest tuple of `equipment_code` values (nulls sort last). Because these tie-breakers are total and deterministic, selection is never arbitrary. If two candidates share an identity but disagree on a field that is *part of* the signature, they by definition have different identities and are **not** collapsed (§12 "must not collapse different …"). Deduplication is idempotent.
**Consequences:** Stable, repeatable result sets; safe under reimported/overlapping source rows. Non-identity metadata differences never change which itinerary appears, only which underlying record backs it. Tested via exact-duplicate collapse, stable-winner, idempotence, and "distinct itineraries preserved" cases (mandated by `PHASE.md` §Tests).
**PRD/TDD sections affected:** TDD §8.6 (itinerary ID derivation); PHASE.md (Phase 3) §11 Deterministic Itinerary Identity, §12 Deduplication
**Approved by:** Project owner (delegated instruction to proceed with Phase 3)

---

## ADR-005: Connection candidate-date and connection-window policy

**Status:** Accepted
**Date:** 2026-07-31
**Context:** `PHASE.md` §6–§8 require one-stop generation to consider second-segment departures on the connection airport's applicable local date and, where needed, the following local date, without assuming both segments share a date or timezone. The candidate operating dates must be derived from the connection airport's local arrival date and the configured connection window (§7), and layover validation is inclusive of the configured min/max (§8).
**Decision:** For a resolved first segment arriving at instant `A` (destination timezone), the engine computes candidate second-segment **operating dates** as the set `{ local_date(A), local_date(A) + 1 day }`, where `local_date` is taken in the **connection airport's** timezone. This two-date window is sufficient because the maximum connection is bounded (`DEFAULT_MAX_CONNECTION_MINUTES`, default 240 min ≤ 24 h), so no valid second departure can fall on a date beyond arrival-date + 1. Each candidate second instance is then subjected to connection validation with **inclusive** bounds: `layover_minutes >= min` and `layover_minutes <= max`, where `layover = second.departure_at - first.arrival_at` computed on absolute (UTC-normalized) instants; zero and negative layovers are rejected. Total itinerary duration must satisfy `<= DEFAULT_MAX_TOTAL_DURATION_MINUTES` (inclusive). If a future policy raises the maximum connection window past 24 h, the candidate-date set must widen accordingly — that change requires a superseding ADR.
**Consequences:** Bounded, index-friendly queries (origin + small date set), avoiding unbounded traversal and satisfying the §Performance "no unbounded traversal" gate. Correctly handles same-day, cross-midnight, and differing-timezone connections. Overnight layovers are permitted only while elapsed layover stays within the configured maximum (§8). Requires boundary tests at exactly min, exactly max, one below min, one above max (mandated by `PHASE.md`).
**PRD/TDD sections affected:** TDD §12.3 (one-stop), §14 (connection validation defaults); PHASE.md (Phase 3) §6 One-Stop Generation, §7 Connection-Date Resolution, §8 Connection Validation
**Approved by:** Project owner (delegated instruction to proceed with Phase 3)

---

## ADR-006: API money is serialized as a decimal string

**Status:** Accepted
**Date:** 2026-08-01
**Context:** Phase 3 represents money as `Decimal` (never float) in `PriceSummary.amount`. The Phase 4 contract (§Serialization Rules) requires money to be "serialized as a decimal-safe string unless the project has an accepted numeric serialization policy," and its `POST /api/v1/search` response example shows `"amount": "14.91"`. JSON numbers are IEEE-754 floats and would reintroduce the exact rounding error the money invariant forbids.
**Decision:** All monetary amounts in public API responses are serialized as decimal strings (e.g. `"14.91"`), produced from the backend `Decimal` via `str()`. An unknown/disabled estimate (`amount is None`) serializes as JSON `null`, never `"0"` or `0`. `currency` is a 3-letter uppercase string. The frontend treats these as opaque display strings and never performs price arithmetic (pricing stays in the backend). This is the project's accepted numeric serialization policy for money.
**Consequences:** No float rounding across the wire; the generated TypeScript type for `amount` is `string | null`. Sorting/filtering by price remains backend-only (the API already applies `max_price` and `PRICE` sort before serialization). Tested by asserting response `amount` is a string equal to the expected decimal and that `null` is preserved for UNKNOWN estimates.
**PRD/TDD sections affected:** TDD §8.7 (PriceSummary), §15 (pricing); PHASE.md (Phase 4) §Serialization Rules, API-002 response
**Approved by:** Project owner (delegated instruction to proceed with Phase 4)

---

## ADR-007: Phase 4 availability envelope is always NOT_CHECKED / LOW

**Status:** Accepted
**Date:** 2026-08-01
**Context:** The Phase 4 search response (API-002) includes an `availability` object `{status, checked_at, source, confidence}` with `confidence` in {LOW, MEDIUM, HIGH}. Phase 3 only carries `Itinerary.availability_status` (`AvailabilityStatus.NOT_CHECKED`); there is no `ConfidenceLevel` type and no live availability provider (explicitly excluded from Phase 4). The contract forbids claiming a scheduled itinerary is available/bookable.
**Decision:** Every Phase 4 itinerary serializes `availability` as `{"status": "NOT_CHECKED", "checked_at": null, "source": null, "confidence": "LOW"}`. `confidence` is a fixed public enum string; `"LOW"` is the honest value when nothing has been verified. The API must never emit `AVAILABLE` for a scheduled itinerary in Phase 4. The frontend renders "Availability not checked" and must not use a green/"available" affordance. A future availability phase may populate real values without changing the field shape.
**Consequences:** Stable response shape ready for later verified availability; honest user communication (PHASE.md §Honest User Communication). Tested by asserting every result's availability is NOT_CHECKED with null checked_at/source and LOW confidence.
**PRD/TDD sections affected:** TDD §8.8 (AvailabilitySummary), §2.2 (confidence levels); PHASE.md (Phase 4) API-002, §Honest User Communication, WEB-003 Availability Display
**Approved by:** Project owner (delegated instruction to proceed with Phase 4)

---

## ADR-008: search_id, generated_at, warnings, and booking_url are response-layer constructs

**Status:** Accepted
**Date:** 2026-08-01
**Context:** The Phase 3 `SearchResult` (`itineraries`, `active_source_name`, `active_source_version`, `diagnostics`) does not carry the `search_id`, `generated_at`, structured `warnings[]`, `data_freshness`, or per-itinerary `booking_url` that the API-002 response example requires.
**Decision:** The API layer (not the routing engine) synthesizes these: `search_id` = a per-request uuid4 (stringified); `generated_at` = a timezone-aware "now" serialized ISO-8601 with offset; `data_freshness` is built from `get_active_schedule_status(db)`; `warnings` is a list of typed `{code, message}` objects — always includes `AVAILABILITY_NOT_CHECKED`, includes `NO_MATCHING_ITINERARIES` when `results` is empty, and `RESULTS_TRUNCATED` when the result cap (ADR: 250) is applied. `booking_url` is `null` in Phase 4 (no stable Frontier deep link is claimed; the frontend renders a non-committal "Check on Frontier" handoff). The routing engine is unchanged.
**Consequences:** Keeps the deterministic engine pure while the HTTP layer owns presentation/metadata. `warnings` being objects (not bare strings) supersedes the older TDD §11 example per the Phase 4 contract's Requirement Authority. Tested via response-shape and no-result/truncation warning assertions.
**PRD/TDD sections affected:** TDD §11 (search response example — superseded for warnings shape); PHASE.md (Phase 4) API-002 response, §No-Result Behavior, §Result Limits
**Approved by:** Project owner (delegated instruction to proceed with Phase 4)

---

## ADR-009: HTTP status mapping and error envelope for the public API

**Status:** Accepted
**Date:** 2026-08-01
**Context:** Phase 4 requires one consistent error schema `{error:{code,message,details?,request_id}}` with a fixed set of stable codes, request IDs on every response, and validation errors distinguished from internal errors without leaking stack traces/SQL. Phase 3 raises typed `RoutingError` subclasses each carrying a `RoutingErrorCode`; Pydantic raises `RequestValidationError` before the engine runs.
**Decision:** A single error envelope is emitted by FastAPI exception handlers. Mapping:
- Pydantic `RequestValidationError` → HTTP 422, code `INVALID_REQUEST`, `details` = per-field errors.
- `UnknownOriginError` (`UNKNOWN_ORIGIN`) → HTTP 422, code `INVALID_AIRPORT`.
- `DateOutsideScheduleRangeError` (`DATE_OUTSIDE_SCHEDULE_RANGE`) → HTTP 422, code `DATE_OUTSIDE_SCHEDULE_RANGE`, `details` = supported range.
- `InvalidTimezoneError` / `InvalidCriteriaError` → HTTP 422, code `INVALID_REQUEST`.
- `NoActiveScheduleError` (`NO_ACTIVE_SCHEDULE`) → HTTP 503, code `NO_ACTIVE_SCHEDULE`.
- Any other/unexpected exception → HTTP 500, code `INTERNAL_ERROR`, generic message (no internals).
Every response carries an `X-Request-ID` header and the same id in the error body's `request_id`. A valid search with zero itineraries is **HTTP 200** (not an error). Airport-search validation (bad `limit`, empty query) → 422 `INVALID_REQUEST`.
**Consequences:** Frontend can branch on stable codes to render expected vs. unexpected errors. No SQL/stack traces reach clients. Public error codes are a stable enum surfaced in OpenAPI. Tested per code path (invalid origin, bad date, out-of-range, conflicting geo filters, unsupported sort, no active schedule, no-result-200, request-id propagation).
**PRD/TDD sections affected:** TDD §24 (error model & codes); PHASE.md (Phase 4) §Public API Error Contract, §No-Result Behavior
**Approved by:** Project owner (delegated instruction to proceed with Phase 4)

---