# Release Checklist

- Install locked Python and pnpm dependencies.
- Run format, lint, type, backend, frontend, OpenAPI/type-generation, mocked E2E, full-stack E2E, timezone/property, and load-smoke commands from `PHASE.md`.
- Run secret, dependency, static-analysis, and container scans; triage all findings. Critical and exploitable high findings block release.
- Build both production containers, migrate a clean ephemeral PostgreSQL database, seed synthetic data, and verify liveness/readiness.
- Verify cached repeat, no-result cache, request IDs, rate limit, metrics protection, Redis outage, and Redis recovery.
- Record the load environment and p50/p95/p99 results in `docs/PERFORMANCE_BASELINE.md`; compare p95 with the prior baseline and investigate degradation above 20%.
- Confirm explicit CORS, CSP/security headers, release tags, alert routing, and no live Frontier requests/credentials.
- Review migrations and rollback. Production deploy remains a separate human approval; CI may stage but must not merge or deploy production automatically.
- After deployment, smoke airport/status/direct/one-stop searches and confirm estimates remain `ESTIMATED` and availability remains `NOT_CHECKED`.
