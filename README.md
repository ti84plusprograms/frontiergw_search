# Frontier GoWild Destination Explorer

Search and discover every Frontier destination reachable from your home airport on a selected date, with estimated GoWild pricing.

## Quick Start

### Prerequisites

- Node.js 22+
- Python 3.10+
- Docker & Docker Compose
- pnpm 10.17+

### Local Development (with Docker Compose)

```bash
docker compose -f infrastructure/docker-compose.yml up
```

Services will be available at:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

### Local Development (without Docker)

#### Backend setup

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements-dev.lock
pip install -e . --no-deps

# Start services first (Postgres + Redis locally or Docker)
export DATABASE_URL="postgresql+psycopg://gowild:gowild@localhost:5432/gowild"
export REDIS_URL="redis://localhost:6379/0"

uvicorn app.main:app --reload
```

#### Frontend setup

```bash
cd apps/web
pnpm install
pnpm dev
```

## Commands

### Backend

```bash
# Install & activate venv
cd apps/api
python -m venv .venv
source .venv/bin/activate

# Install locked dependencies
pip install -r requirements-dev.lock
pip install -e . --no-deps

# Format & lint
ruff format .
ruff check --fix

# Type check
mypy app

# Run tests
pytest tests/ -v

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Phase 2 data ingestion (run from apps/api with the backend environment active)
python -m app.cli airport-seed data/fixtures/sample_airports.csv
python -m app.cli schedule-validate data/fixtures/sample_schedule.csv
python -m app.cli schedule-import data/fixtures/sample_schedule.csv
python -m app.cli schedule-status
```

Schedule imports use the provider source version and a canonical checksum of the
complete normalized dataset. Re-importing identical content is a reported no-op;
reusing a source version with different content fails without changing the active
dataset. Import failures return a nonzero command status and leave the prior active
dataset unchanged.

#### Phase 3 routing engine

The deterministic itinerary search engine (Phase 3, tasks RTE-001–RTE-007) is a
backend service layer — there is no public search HTTP endpoint yet (that is Phase 4,
API-002). Search over the active schedule dataset by calling
`app.services.routing.engine.search_itineraries(db, SearchCriteria(...))`, which returns
direct and one-stop itineraries with timezone-aware times and clearly labeled
**estimated** GoWild pricing. All routing is deterministic and never uses an LLM.

Routing configuration (centralized in `app/core/config.py`, overridable by environment
variable; invalid values fail at service initialization):

```text
DEFAULT_MIN_CONNECTION_MINUTES=45
DEFAULT_MAX_CONNECTION_MINUTES=240
DEFAULT_MAX_TOTAL_DURATION_MINUTES=720
DOMESTIC_ESTIMATED_SEGMENT_PRICE_USD=14.91   # Decimal, never float
INTERNATIONAL_ESTIMATION_ENABLED=false
MAX_SUPPORTED_CONNECTIONS=1
```

DST-ambiguous/nonexistent local times, deduplication precedence, and the connection
candidate-date window are governed by ADR-003/004/005 in `DECISIONS.md`.

Routing tests: pure-domain unit and property-based tests run on SQLite; the integration
suite and performance benchmark require PostgreSQL and are skipped otherwise.

```bash
# Routing-focused backend tests (SQLite; integration/perf auto-skip)
pytest tests/ -v

# Full suite incl. PostgreSQL integration + performance benchmark
DATABASE_URL_TEST=postgresql+psycopg://gowild:gowild@localhost:5432/gowild pytest tests/ -v
```

### Frontend

```bash
# Install dependencies
cd apps/web
pnpm install

# Develop
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 pnpm dev

# Type check
pnpm type-check

# Lint
pnpm lint

# Unit, component, and accessibility tests
pnpm test

# Browser tests (desktop, mobile, keyboard, and accessibility)
pnpm exec playwright install chromium
pnpm test:e2e

# Full-stack browser tests (requires the seeded Docker stack)
pnpm test:e2e:fullstack

# Verify generated API types are current
pnpm check:types

# Build
pnpm build
```

Search and results URLs use normalized query parameters so refresh, sharing, and
browser navigation preserve criteria. Supported parameters are `origin`, `date`,
`connections`, `min_conn`, `max_conn`, `depart_after`, `depart_before`,
`arrive_before`, `max_duration`, `max_price`, `domestic`, `international`, and
`sort`. Standard defaults are omitted from generated URLs; malformed or
contradictory values are rejected instead of being silently applied.

### Docker Compose

```bash
docker compose -f infrastructure/docker-compose.yml up
docker compose -f infrastructure/docker-compose.yml logs -f api
docker compose -f infrastructure/docker-compose.yml down
```

## Project Structure

```
apps/
  api/           Python FastAPI backend
  web/           Next.js React frontend
packages/        Shared libraries (future)
infrastructure/  Docker, deployment configs
docs/            PRD, TDD, and other docs
```

## Documentation

- [Product Requirements Document](docs/PRD.md)
- [Technical Design Document](docs/TDD.md)
- [Architecture Decisions](DECISIONS.md)
- [Implementation Tasks](TASKS.md)
- [Operations Runbook](docs/RUNBOOK.md)
- [Caching](docs/CACHING.md)
- [Monitoring](docs/MONITORING.md)
- [Incident Response](docs/INCIDENT_RESPONSE.md)
- [Release Checklist](docs/RELEASE_CHECKLIST.md)
- [Performance Baseline](docs/PERFORMANCE_BASELINE.md)

## Development Workflow

1. Read PRD and TDD before starting.
2. Check DECISIONS.md for approved design choices.
3. Review TASKS.md for current work status.
4. Make focused, single-concern commits.
5. Run formatters, linters, type checks, and tests before pushing.
6. Update TASKS.md when work is complete.
