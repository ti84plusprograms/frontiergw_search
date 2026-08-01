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