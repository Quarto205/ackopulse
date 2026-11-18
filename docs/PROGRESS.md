# PROGRESS

Update at the end of each unit (CLOSE prompt). Times are minutes.

## Current
- Current unit: Unit 4 Complete (ready for Unit 5)
- Branch: unit-1
- Last commit: f2a58e7

## Units

| Unit | Name | Est. | Actual | Status | Tests (pass/total) | Branch | Notes |
|---|---|---|---|---|---|---|---|
| U0 | Wiring | 8 | 10 | DONE | 1/1 | 00-wiring | Dockerfile, compose, pytest.ini, Makefile, smoke /health |
| U1 | Backend + DB | 12 | 15 | DONE | 9/9 | 01-backend-db | Schema, aiosqlite, seed, catalogue API, validations |
| U2 | Health-check engine | 18 | 16 | DONE | 9/9 | 02-health-checks | Scheduler+probe, shared httpx client, D-11..D-15 |
| U3 | State + incident engine | 18 | 15 | DONE | 16/16 | 03-state-incidents | Pure classifier, transitions, single active incident, ack, notes |
| U4 | Operator UI | 14 | 12 | DONE | 15/15 | 04-operator-ui | Dashboard, recent latencies, incident detail, ack, notes, registration form |
| U5 | Public status page | 8 | | NOT STARTED | | 05-public-page | |
| U6 | Notifications + metrics | 18 | | NOT STARTED | | 06-notify-metrics | |
| U7 | Verification + handover | 16 | | NOT STARTED | | 07-verification | |

Status values: NOT STARTED, IN PROGRESS, DONE, CUT (thin form), ROLLED BACK.

## Must-have coverage

| # | Must-have | Unit | Status |
|---|---|---|---|
| 1 | Service catalogue (API + UI) | U1, U4 | DONE (API + registration form & dashboard UI) |
| 2 | Health checking | U2 | DONE (scheduler + probe, 9 tests) |
| 3 | Service state | U3 | DONE (deterministic classification & transitions) |
| 4 | Incidents | U3, U4 | DONE (engine, lifecycle, timeline, ack, notes) |
| 5 | Reliability tracking | U6 | NOT STARTED |
| 6 | Operator dashboard | U4 | DONE (/ops dashboard, timeline, recent latencies) |
| 7 | Public status page | U5 | NOT STARTED |
| 8 | Notifications | U6 | NOT STARTED |
| 9 | Product metrics | U2, U6 | Checker stats in U2; reliability in U6 |
| 10 | Runnable | U0, U7 | U0 runnable |

## Gates
- Gate 1: PLAN.md committed by 1:15. Status: Complete
- Gate 2: working backend + this file committed by 3:30. Status: Complete (Units 0-4 done, 50/50 tests passing)

## What works / what remains
- Works:
  - Unit 0: FastAPI application structure, config, Dockerfile, docker-compose.yml, Makefile, pytest setup, and /health smoke test.
  - Unit 1: aiosqlite database connection with WAL mode and foreign key support; full schema creation with partial unique index for active incidents; idempotent seeding of the four starter-kit mock services (quotes, payments, claims, notifications); catalogue management with validation and duplicate prevention; REST API endpoints (`GET /api/services`, `POST /api/services`, `GET /api/services/{id}`).
  - Unit 2: Asynchronous HTTP check probe with timeout bound, concurrent execution across due services, lag and duration capture, overlap skip with counter.
  - Unit 3: Pure state classification (`observe()`, `classify_raw_probe()`), deterministic transitions across HEALTHY, DEGRADED, DOWN, single-active incident enforcement, recovery resolution, operator acknowledgement, notes, and timeline events in a single transaction.
  - Unit 4: Operator UI under `/ops`: live dashboard with auto-refresh meta tag, service health status badges, recent response time spark badges ($N=5$), active incidents list with acknowledgment status, resolved incidents history, incident detail view with chronological timeline, idempotent acknowledge action, operator note appending with HTML-escaping, and service registration form (`/ops/services/new`). Root `/` redirects to `/ops`.
- Remains:
  - Unit 5: Public status page (`/status` read-only customer view, strict privacy isolation).
  - Unit 6: Webhook notifications & reliability metrics.
  - Unit 7: Acceptance test drill and documentation.
- Known limitations:
  - Webhooks are pending Unit 6.
  - Public status page pending Unit 5.
