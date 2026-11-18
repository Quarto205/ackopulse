# AGENTS.md — rules for any AI agent working in this repo

Project: Pulse, a service status and incident hub. Stack: FastAPI, SQLite (aiosqlite), httpx.AsyncClient, server-rendered Jinja2 (pending D-entry, see DECISIONS.md).

## Read first
1. `PROGRESS.md` for the current unit and status.
2. `DECISIONS.md` for every threshold, rule and policy. It is the only source of truth for them.
3. `docs/STARTER_KIT.md` for ports, hostnames, endpoints and webhook shape.
4. `ARCHITECTURE.md` and `PROJECT_STRUCTURE.md` for where code goes.

## Hard rules
- Never decide a threshold, timeout, retry count, privacy rule or metric definition. If `DECISIONS.md` lacks it, stop and list 2-3 options with minutes and test impact. No recommendation.
- Tests first. Write failing tests, show they fail for the right reason, then wait for "go".
- Stay inside the file list for the current unit. Do not touch other files.
- Same test fails twice for the same cause: stop and show the failure. No third attempt.
- No new libraries beyond those named in `DECISIONS.md`.
- Never await a webhook inside the check loop.
- No authentication, Redis, Celery, Kubernetes or extra monitoring stack (out of scope).
- Store UTC. Use the injected clock, never `datetime.now()` directly in product code.
- Never commit. Never edit `PLAN.md`.
- Public page uses its own data model. It must never expose health URL, owner, notes or acknowledge info.

## Test conventions
- pytest markers `unit_00` to `unit_07`. Run with `make test U=<nn>`; `make test` runs everything.
- Unit and integration tests use in-process fake HTTP servers and an injected clock, not the real compose stack.
- No test sleeps longer than 1 s.

## Output conventions
- Review prompts: max 8 findings by severity, then 3 lines per changed file (what and why).
- Close-out updates `PROGRESS.md`, `docs/TESTS.md` and `LOG.md`.
