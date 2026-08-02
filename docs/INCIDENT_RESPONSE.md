# Incident Response

Severity 1 covers total outage, database loss, leaked secrets, or confirmed incorrect route/time/price output. Stop or disable search when deterministic correctness or price labeling is in doubt, preserve logs/request IDs, notify the owner, and do not restore traffic until a regression test proves the correction. Rotate exposed secrets immediately.

Severity 2 covers elevated 5xx, sustained latency, no active/expired schedule, failed imports, or widespread frontend failures. Triage current release, readiness, schedule status, database metrics, and recent changes; roll back when the fault follows a release.

Severity 3 covers Redis or monitoring outage, isolated errors, and rate-limit spikes. Redis and monitoring are degradable: confirm core search remains correct, then repair the optional dependency without disabling PostgreSQL-backed search.

For every incident, record UTC start/end, release, schedule version, request IDs, user-visible impact, commands/actions, and follow-up tests. Never paste authorization/cookie headers, DSNs, database/Redis URLs, passports, payment data, or full request payloads into tickets. Incorrect timezone display must be checked across database definition, domain instance, API offset, and frontend rendering. Incorrect estimated price requires disabling the affected estimator or search rather than relabeling an estimate as verified.
