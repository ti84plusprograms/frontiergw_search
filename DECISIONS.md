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