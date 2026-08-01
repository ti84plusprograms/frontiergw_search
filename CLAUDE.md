# Claude Code Instructions

## Source of truth

Before planning or modifying code, read:

1. `PHASE.md` defines the exact scope and exit gate for the active phase.
2. `docs/PRD.md` for product behavior and scope.
3. `docs/TDD.md` for architecture, contracts, schemas, algorithms, and implementation constraints.
4. `TASKS.md` for current work status.
5. `DECISIONS.md` for approved deviations and architectural decisions.

`PHASE.md` is overwritten in place at each phase transition. Prior phase contracts are
not archived under `docs/phases/`; the `phase-N-complete` git tag preserves each contract
at the commit it governed (recover with `git show phase-N-complete:PHASE.md`).

The PRD controls what the product must do. The TDD controls how the product should be implemented.

If the PRD and TDD conflict, stop implementation and document the conflict in your response. Do not silently choose one.

## Working method

For every substantial task:

1. Inspect the relevant repository files.
2. State the applicable PRD and TDD requirements.
3. Produce a bounded implementation plan.
4. Identify files to create or modify.
5. Implement only the approved task.
6. Run the relevant formatters, linters, type checks, and tests.
7. Review the resulting diff.
8. Update `TASKS.md`.
9. Update documentation when behavior or architecture changes.

## Engineering rules

- Keep flight routing deterministic.
- Do not use an LLM to generate routes, prices, schedules, or availability.
- Use timezone-aware datetimes.
- Use `Decimal`, PostgreSQL `NUMERIC`, or integer cents for money.
- Never represent estimated prices as verified prices.
- Do not store Frontier credentials.
- Do not implement Frontier browser automation unless an approved decision in `DECISIONS.md` explicitly authorizes it.
- Do not expose provider-specific fields through the public API.
- Do not change database schemas without an Alembic migration.
- Do not modify public API contracts without updating OpenAPI, tests, frontend types, and relevant documentation.
- Add a regression test for every defect fixed.
- Prefer small, reviewable commits.
- Do not add dependencies unless necessary and documented.

## Commands

Once the repository is initialized, maintain the authoritative commands below:

- **Install:** `cd apps/api && python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"` (backend); `pnpm install` (frontend)
- **Start development:** `docker compose -f infrastructure/docker-compose.yml up` or `make dev`
- **Format:** Backend: `cd apps/api && source .venv/bin/activate && ruff format .`
- **Lint:** Backend: `cd apps/api && source .venv/bin/activate && ruff check`; Frontend: `cd apps/web && pnpm lint`
- **Type check:** Backend: `cd apps/api && source .venv/bin/activate && mypy app`; Frontend: `cd apps/web && pnpm type-check`
- **Unit tests:** Backend: `cd apps/api && source .venv/bin/activate && pytest tests/ -v`
- **Integration tests:** (deferred to Phase 5)
- **End-to-end tests:** (deferred to Phase 5)
- **Build:** Frontend: `cd apps/web && pnpm build`; Docker: `docker compose -f infrastructure/docker-compose.yml build`

See `Makefile` for convenience targets.
