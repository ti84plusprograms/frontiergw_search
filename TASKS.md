# Implementation Tasks

## Status values

- NOT STARTED
- IN PROGRESS
- BLOCKED
- IN REVIEW
- COMPLETE

## Phase 1 — Foundation

| ID | Task | Owner | Status | Dependencies |
|---|---|---|---|---|
| FND-001 | Initialize monorepo | Claude | COMPLETE | None |
| FND-002 | Configure local Docker environment | Claude | COMPLETE | FND-001 |
| FND-003 | Configure FastAPI application | Claude | COMPLETE | FND-001 |
| FND-004 | Configure Next.js application | Claude | COMPLETE | FND-001 |
| FND-005 | Configure PostgreSQL and Alembic | Claude | COMPLETE | FND-002 |
| FND-006 | Configure Redis | Claude | COMPLETE | FND-002 |
| FND-007 | Configure CI | Claude | COMPLETE | FND-003, FND-004 |
| FND-008 | Implement health endpoint | Claude | COMPLETE | FND-003, FND-005 |

## Phase 2 — Data and ingestion

| ID | Task | Owner | Status | Dependencies |
|---|---|---|---|---|
| DAT-001 | Implement airport schema and seed import | Claude | COMPLETE | FND-005 |
| DAT-002 | Implement data-source schema | Claude | COMPLETE | FND-005 |
| DAT-003 | Implement route and scheduled-flight schemas | Claude | COMPLETE | DAT-001, DAT-002 |
| DAT-004 | Implement static schedule-provider interface | Claude | COMPLETE | DAT-003 |
| DAT-005 | Implement atomic schedule import | Claude | COMPLETE | DAT-004 |
| DAT-006 | Implement schedule quality checks | Claude | COMPLETE | DAT-005 |

## Phase 3 — Search engine

| ID | Task | Owner | Status | Dependencies |
|---|---|---|---|---|
| RTE-001 | Build timezone-aware flight instances | Claude | COMPLETE | DAT-003 |
| RTE-002 | Implement direct itinerary search | Claude | COMPLETE | RTE-001 |
| RTE-003 | Implement one-stop itinerary search | Claude | COMPLETE | RTE-002 |
| RTE-004 | Implement connection validation | Claude | COMPLETE | RTE-003 |
| RTE-005 | Implement itinerary deduplication | Claude | COMPLETE | RTE-003 |
| RTE-006 | Implement filters and sorting | Claude | COMPLETE | RTE-002 |
| RTE-007 | Implement estimated pricing | Claude | COMPLETE | RTE-002 |

## Phase 4 — API and frontend

| ID | Task | Owner | Status | Dependencies |
|---|---|---|---|---|
| API-001 | Implement airport search endpoint | Claude | COMPLETE | DAT-001 |
| API-002 | Implement itinerary search endpoint | Claude | COMPLETE | RTE-006, RTE-007 |
| API-003 | Implement schedule-status endpoint | Claude | COMPLETE | DAT-005 |
| WEB-001 | Build search form | Claude | COMPLETE | FND-004, API-001 |
| WEB-002 | Build results list | Claude | COMPLETE | API-002 |
| WEB-003 | Build itinerary card | Claude | COMPLETE | WEB-002 |
| WEB-004 | Add filters, sorting, and URL state | Claude | COMPLETE | WEB-002 |

## Phase 5 — Hardening

| ID | Task | Owner | Status | Dependencies |
|---|---|---|---|---|
| OPS-001 | Add caching | Codex | IN REVIEW | API-002 |
| OPS-002 | Add structured logging | Codex | IN REVIEW | API-002 |
| OPS-003 | Add rate limiting | Codex | IN REVIEW | API-002 |
| OPS-004 | Add monitoring and error reporting | Codex | IN REVIEW | OPS-002 |
| QA-001 | Add end-to-end tests | Codex | IN REVIEW | WEB-004 |
| QA-002 | Add routing and API performance tests | Codex | IN REVIEW | RTE-006 |
| QA-003 | Add timezone edge-case suite | Codex | IN REVIEW | RTE-004 |

Agents should update statuses, but they must not delete incomplete tasks.
