# Pulse — Service Status and Incident Hub

Pulse watches HTTP health endpoints, classifies service state, opens and resolves incidents automatically, notifies a webhook, and shows an operator dashboard and a read-only public status page.

## Quick start (one command)
```bash
make up
```
- App / Root redirect: http://localhost:8000 (redirects to `/ops`)
- Operator dashboard: http://localhost:8000/ops
- Public status page: http://localhost:8000/status
- Health check endpoint: http://localhost:8000/health

Requirements: Docker, Docker Compose, or local Python 3.11+. The supplied starter-kit services run on ports 7001–7004 with the webhook receiver on 9900 (see `docs/STARTER_KIT.md`).

## Local Development (without Docker)
```bash
# Terminal 1: run starter kit mock services and webhook receiver
python scripts/run_starter_kit.py

# Terminal 2: run Pulse development server
uvicorn src.pulse.main:app --host 0.0.0.0 --port 8000 --reload
```

## Configuration
Copy `.env.example` to `.env`. Keys: DB path, check timeout, degraded threshold, failure threshold, recovery threshold, webhook URL. Values are documented in `DECISIONS.md`.

## Tests
```bash
make test          # all 69 unit and integration tests
make test U=02     # specific unit marker (unit_00 to unit_07)
make acceptance    # full end-to-end failure-to-recovery drill (< 90 s)
make secrets-check # credential scanning across repo files
```

## Demo path
1. All four mock services healthy (quotes, payments, claims, notifications).
2. Trigger payments `/control/down`.
3. After the failure threshold (2 checks): payments transitions to DOWN, an incident opens, timeline entry logged, and webhook delivered.
4. Operator acknowledges the incident and adds a note via `/ops/incidents/{id}`.
5. Trigger payments `/control/reset`.
6. After the recovery threshold (2 healthy checks): payments transitions to HEALTHY, incident resolves, recovery webhook delivered, and public page updates.
7. Metrics show MTTD, MTTR, availability estimate, and error budget.

## Working features (verified)
- **Service Catalogue**: SQLite persistence with unique slug validation, schema constraints, and registration API (`/api/services`) + UI form (`/ops/services/new`).
- **Health-Check Engine**: Concurrent async polling with timeout enforcement, overlap protection (`skipped_runs`), lag and execution duration capture.
- **State Classification**: Deterministic state machine (HEALTHY, DEGRADED, DOWN) based on HTTP status, latency threshold (1500 ms), and consecutive counts.
- **Incident Lifecycle**: Automated incident creation on DOWN, recovery resolution on 2 healthy checks, single active incident guard, chronological timeline with operator acknowledge and note logging.
- **Operator Dashboard**: Live overview (`/ops`) with 5s auto-refresh, recent latency badges, incident queue, acknowledge action, note entry, and service registration.
- **Public Status Page**: Customer-facing read-only view (`/status`) with collapsed states (UP, ISSUE, OUTAGE), rolling 24h history, and strict privacy isolation preventing leaks of health URLs, owners, or notes.
- **Notifications**: Background webhook sender with bounded retries (3 attempts), 2s backoff, SQLite delivery attempt logging, and idempotency key guard (`{incident_id}:{event_type}`).
- **Reliability Metrics**: Sampled rolling 24h availability, target SLO, error budget remaining (floored at 0), MTTD, MTTR, and checker performance metrics labeled as periodic check estimates.
- **Acceptance Automation**: End-to-end failure-to-recovery drill script (`scripts/acceptance.py`) finishing in under 90 seconds.

## Limitations
- **No authentication / RBAC**: Designed for local operator demo; no user login or role-based access control.
- **Sampled estimates**: Availability and error budget figures are periodic check estimates, not continuous network monitoring.
- **Single-instance storage**: Uses local SQLite in WAL mode; not distributed across multiple host nodes.
- **Single-tenant status**: Public page serves the single organization's status without multi-tenant domain mapping.

## Documents
- `PLAN.md` product plan · `ARCHITECTURE.md` design · `PROJECT_STRUCTURE.md` layout
- `DECISIONS.md` decisions · `REVIEW.md` self-assessment · `LOG.md` AI events
- `docs/` statement, questions, starter-kit recon, tests

## AI use (declared)
| Tool / model | Used for | Where (units) | Transcript |
|---|---|---|---|
| Antigravity + Pro / Claude | Architecture planning, unit prompts, test generation | Units 0–7 | transcripts/ |
| Antigravity + Flash | Boilerplate scaffolding, fast refactoring | Units 1–6 | transcripts/ |
| NotebookLM / other chats | Initial problem statement decomposition & planning | Preparation | transcripts/prep/ |

I reviewed and can explain all code. Decisions in DECISIONS.md are my own.
