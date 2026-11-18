# PROGRESS

Update at the end of each unit (CLOSE prompt). Times are minutes.

## Current
- Current unit: Unit 6 Complete (ready for Unit 7)
- Branch: main
- Last commit: -

## Units

| Unit | Name | Est. | Actual | Status | Tests (pass/total) | Branch | Notes |
|---|---|---|---|---|---|---|---|
| U0 | Wiring | 8 | 10 | DONE | 1/1 | 00-wiring | Dockerfile, compose, pytest.ini, Makefile, smoke /health |
| U1 | Backend + DB | 12 | 15 | DONE | 9/9 | 01-backend-db | Schema, aiosqlite, seed, catalogue API, validations |
| U2 | Health-check engine | 18 | 16 | DONE | 9/9 | 02-health-checks | Scheduler+probe, shared httpx client, D-11..D-15 |
| U3 | State + incident engine | 18 | 15 | DONE | 16/16 | 03-state-incidents | Pure classifier, transitions, single active incident, ack, notes |
| U4 | Operator UI | 14 | 12 | DONE | 15/15 | 04-operator-ui | Dashboard, recent latencies, incident detail, ack, notes, registration form |
| U5 | Public status page | 8 | 12 | DONE | 6/6 | 05-public-page | /status read-only, D-20/21/22, privacy leak tests, 56/56 total |
| U6 | Notifications + metrics | 18 | 20 | DONE | 10/10 | 06-notify-metrics | Sender D-23/24/28, metrics D-25/26/27, /api/metrics/summary, 66/66 total |
| U7 | Verification + handover | 16 | | NOT STARTED | | 07-verification | |

Status values: NOT STARTED, IN PROGRESS, DONE, CUT (thin form), ROLLED BACK.

## Must-have coverage

| # | Must-have | Unit | Status |
|---|---|---|---|
| 1 | Service catalogue (API + UI) | U1, U4 | DONE (API + registration form & dashboard UI) |
| 2 | Health checking | U2 | DONE (scheduler + probe, 9 tests) |
| 3 | Service state | U3 | DONE (deterministic classification & transitions) |
| 4 | Incidents | U3, U4 | DONE (engine, lifecycle, timeline, ack, notes) |
| 5 | Reliability tracking | U6 | DONE (availability/budget/MTTD/MTTR via /api/metrics/summary) |
| 6 | Operator dashboard | U4 | DONE (/ops dashboard, timeline, recent latencies) |
| 7 | Public status page | U5 | DONE (/status, 6 tests, no leaks) |
| 8 | Notifications | U6 | DONE (webhook sender, pending rows, retries) |
| 9 | Product metrics | U2, U6 | DONE (checker stats in U2; reliability in U6) |
| 10 | Runnable | U0, U7 | U0 runnable |

## Gates
- Gate 1: PLAN.md committed by 1:15. Status: Complete
- Gate 2: working backend + this file committed by 3:30. Status: Complete (Units 0-6 done, 66/66 tests passing)

## What works / what remains
- Works:
  - Unit 0: FastAPI application structure, config, Dockerfile, docker-compose.yml, Makefile, pytest setup, and /health smoke test.
  - Unit 1: aiosqlite database connection with WAL mode and foreign key support; full schema creation with partial unique index for active incidents; idempotent seeding of the four starter-kit mock services (quotes, payments, claims, notifications); catalogue management with validation and duplicate prevention; REST API endpoints (`GET /api/services`, `POST /api/services`, `GET /api/services/{id}`).
  - Unit 2: Asynchronous HTTP check probe with timeout bound, concurrent execution across due services, lag and duration capture, overlap skip with counter.
  - Unit 3: Pure state classification (`observe()`, `classify_raw_probe()`), deterministic transitions across HEALTHY, DEGRADED, DOWN, single-active incident enforcement, recovery resolution, operator acknowledgement, notes, and timeline events in a single transaction.
  - Unit 4: Operator UI under `/ops`: live dashboard with auto-refresh meta tag, service health status badges, recent response time spark badges ($N=5$), active incidents list with acknowledgment status, resolved incidents history, incident detail view with chronological timeline, idempotent acknowledge action, operator note appending with HTML-escaping, and service registration form (`/ops/services/new`). Root `/` redirects to `/ops`.
  - Unit 5: Public status page under `/status`: customer-facing, read-only view with collapsed states (UP, ISSUE, OUTAGE), rolling 24h incident history, strict data isolation guaranteeing zero leaks of internal health URLs, owner details, or operator notes.
  - Unit 6: Automated webhook delivery on incident open and resolve with bounded retries (3 attempts), delivery attempt records in SQLite, idempotency enforcement, and pure metrics calculations for rolling 24-hour sampled availability, error budget remaining, MTTD, MTTR, exposed via `/api/metrics/summary`.
- Remains:
  - Unit 7: Acceptance test drill script (`scripts/acceptance.py`), final verification, and documentation wrap-up.
