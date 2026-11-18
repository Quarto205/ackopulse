# DECISIONS

Every decision is written in my own words, with my own reason.
Entry format: `[D-nn: my decision, alternatives, my reason, origin]`
Origin is one of: my own call, product owner answer, starter kit, AI suggestion I accepted.
Append only, with a timestamp from `date`. Do not edit old entries; add a new one that supersedes.

## Log

- [D-01: Degraded latency threshold is 1.5s, alternatives: 1.0s or 2.0s, reason: 1.5s matches PLAN.md default and distinguishes normal response times from simulated slow mode (3.0s), origin: product owner default in PLAN.md] (2026-11-18 18:15:00 UTC)
- [D-02: Incident trigger is 2 consecutive failed checks, alternatives: 1 failure or 3 failures, reason: 1 failure marks service DEGRADED preventing noisy alerts; 2 consecutive confirms true outage and marks DOWN, origin: product owner default in PLAN.md] (2026-11-18 18:15:00 UTC)
- [D-03: Recovery trigger is 2 consecutive healthy checks (HTTP 2xx < 1.5s), alternatives: 1 healthy check or 3 healthy checks, reason: avoids flapping on intermittent recovery; slow success remains DEGRADED and does not count towards recovery, origin: product owner default in PLAN.md] (2026-11-18 18:15:00 UTC)
- [D-04: Availability window is rolling 24 hours, alternatives: calendar day or rolling 7 days, reason: standard 24h rolling window clearly labelled as sampled estimate, origin: product owner default in PLAN.md] (2026-11-18 18:15:00 UTC)
- [D-05: Default SLO target is 99.9%, alternatives: 99.0% or 99.99%, reason: standard three-nines target for internal mock services, editable per service, origin: product owner default in PLAN.md] (2026-11-18 18:15:00 UTC)
- [D-06: Webhook receiver payload format sends JSON event with incident and service metadata, alternatives: raw text or form-encoded, reason: starter kit webhook receiver displays JSON cleanly in table, origin: starter kit recon] (2026-11-18 18:15:00 UTC)
- [D-07: Stack is FastAPI + aiosqlite + Jinja2 server-rendered templates, alternatives: separate React frontend or Django, reason: single-process asyncio app without build-step overhead, ensures 100% reliable local demo, origin: ARCHITECTURE.md & PLAN.md] (2026-11-18 18:15:00 UTC)
- [D-08: Check probe timeout is 2.0s with per-service independent execution, alternatives: 1.0s or 5.0s, reason: 2.0s allows detecting normal latency (<1.5s) while cutting off down/slow checks without starving the scheduler loop, origin: my own call] (2026-11-18 18:15:00 UTC)
- [D-09: One active incident per service enforced via SQLite partial unique index (`WHERE status = 'active'`), alternatives: application-level check only, reason: prevents race conditions and duplicate active incidents at the database level, origin: ARCHITECTURE.md] (2026-11-18 18:15:00 UTC)
- [D-10: Strict data isolation for public status page: public view models exclude health_url, owner, internal errors, operator notes and acknowledgement details, alternatives: single shared model with filtered fields, reason: security guarantee against data leaks, origin: AGENTS.md hard rule] (2026-11-18 18:15:00 UTC)
