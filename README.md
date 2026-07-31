# Frontier GoWild Destination Explorer

Search and discover every Frontier destination reachable from your home airport on a selected date, with estimated GoWild pricing.

## Quick Start

### Prerequisites

- Node.js 22+
- Python 3.10.6
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
pip install -e ".[dev]"

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

# Install dependencies
pip install -e ".[dev]"

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
```

The initial migration creates the airport catalog and seeds the Phase 1 airport
autocomplete data. The API container runs `alembic upgrade head` before starting
Uvicorn. For a local backend without Docker, run the migration after starting
PostgreSQL and Redis.

The API health endpoint is a readiness check: `/api/v1/health` returns `200`
only when PostgreSQL and Redis respond, and `503` otherwise. `/api/v1/live` is a
dependency-free liveness check. Configure non-development service URLs
explicitly; production does not accept the local development credentials.

### Frontend

```bash
# Install dependencies
cd apps/web
pnpm install

# Develop
pnpm dev

# Type check
pnpm type-check

# Lint
pnpm lint

# Build
pnpm build
```

### Docker Compose

```bash
docker compose -f infrastructure/docker-compose.yml up
docker compose -f infrastructure/docker-compose.yml logs -f api
docker compose -f infrastructure/docker-compose.yml down
```

Compose keeps PostgreSQL and Redis on the internal service network rather than
publishing their ports to the host. Only the API and web ports are exposed.

### Frontend checks

```bash
pnpm run test:web
pnpm run test:e2e:web
pnpm --filter gowild-web type-check
pnpm run lint:web
pnpm run build:web
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

## Development Workflow

1. Read PRD and TDD before starting.
2. Check DECISIONS.md for approved design choices.
3. Review TASKS.md for current work status.
4. Make focused, single-concern commits.
5. Run formatters, linters, type checks, and tests before pushing.
6. Update TASKS.md when work is complete.
