# Codex Repository Instructions

## Required context

Before making changes, read:

- `docs/PRD.md`
- `docs/TDD.md`
- `TASKS.md`
- `DECISIONS.md`
- Relevant tests and implementation files

The PRD defines product requirements. The TDD defines the expected implementation design. Do not infer missing requirements from convenience. Record unresolved conflicts or ambiguities instead of silently changing scope.

## Required workflow

For each task:

1. Inspect the current repository state.
2. Identify the relevant requirements.
3. Explain the intended change briefly.
4. Make the smallest complete change.
5. Run applicable verification commands.
6. Inspect the complete diff.
7. Report:
   - Files changed
   - Tests run
   - Failures or limitations
   - Requirements satisfied
   - Remaining risks

## Hard constraints

- Routing, scheduling, connection validation, pricing, and availability status are deterministic backend concerns.
- LLMs must not invent flight data.
- All datetimes must be timezone-aware.
- All money calculations must use exact decimal or integer representations.
- Estimates and verified prices must use separate statuses.
- No Frontier passwords, payment data, or passport data may be stored.
- Browser automation is disabled unless explicitly approved in `DECISIONS.md`.
- Provider-specific response structures must remain inside provider adapters.
- Schema changes require migrations.
- Public contract changes require updated schemas, tests, generated types, and documentation.
- Defect fixes require regression tests.
- Never weaken tests merely to make CI pass.

## Review priorities

During review, prioritize:

1. Incorrect route generation
2. Timezone and date errors
3. Invalid connections
4. Incorrect price labeling
5. Security or privacy defects
6. API-contract drift
7. Migration safety
8. Missing failure handling
9. Insufficient tests
10. Maintainability

## Commands

Use the commands recorded in `CLAUDE.md` and the root `README.md`. Do not invent replacement commands when documented commands fail. Diagnose the failure or report it.
