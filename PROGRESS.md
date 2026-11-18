# PROGRESS

Update at the end of each unit (CLOSE prompt). Times are minutes.

## Current
- Current unit: Unit 1 Complete (ready for Unit 2)
- Branch: main
- Last commit: -

## Units

| Unit | Name | Est. | Actual | Status | Tests (pass/total) | Branch | Notes |
|---|---|---|---|---|---|---|---|
| U0 | Wiring | 8 | 10 | DONE | 1/1 | 00-wiring | Dockerfile, compose, pytest.ini, Makefile, smoke /health |
| U1 | Backend + DB | 12 | 15 | DONE | 9/9 | 01-backend-db | Schema, aiosqlite, seed, catalogue API, validations |
| U2 | Health-check engine | 18 | | NOT STARTED | | 02-health-checks | |
| U3 | State + incident engine | 18 | | NOT STARTED | | 03-state-incidents | |
| U4 | Operator UI | 14 | | NOT STARTED | | 04-operator-ui | |
| U5 | Public status page | 8 | | NOT STARTED | | 05-public-page | |
| U6 | Notifications + metrics | 18 | | NOT STARTED | | 06-notify-metrics | |
| U7 | Verification + handover | 16 | | NOT STARTED | | 07-verification | |

Status values: NOT STARTED, IN PROGRESS, DONE, CUT (thin form), ROLLED BACK.

## Must-have coverage

| # | Must-have | Unit | Status |
|---|---|---|---|
| 1 | Service catalogue (API + UI) | U1, U4 | API DONE, UI pending |
| 2 | Health checking | U2 | NOT STARTED |
| 3 | Service state | U3 | NOT STARTED |
| 4 | Incidents | U3, U4 | NOT STARTED |
| 5 | Reliability tracking | U6 | NOT STARTED |
| 6 | Operator dashboard | U4 | NOT STARTED |
| 7 | Public status page | U5 | NOT STARTED |
| 8 | Notifications | U6 | NOT STARTED |
| 9 | Product metrics | U2, U6 | NOT STARTED |
| 10 | Runnable | U0, U7 | U0 runnable |

## Gates
- Gate 1: PLAN.md committed by 1:15. Status: Complete
- Gate 2: working backend + this file committed by 3:30. Status: In progress

## What works / what remains
- Works:
  - Unit 0: FastAPI application structure, config, Dockerfile, docker-compose.yml, Makefile, pytest setup, and /health smoke test.
  - Unit 1: aiosqlite database connection with WAL mode and foreign key support; full schema creation with partial unique index for active incidents; idempotent seeding of the four starter-kit mock services (quotes, payments, claims, notifications); catalogue management with validation and duplicate prevention; REST API endpoints (`GET /api/services`, `POST /api/services`, `GET /api/services/{id}`).
- Remains:
  - Unit 2: Health-check engine (probe, timeout, async execution, persistence).
  - Unit 3: State classification & incident engine.
  - Unit 4: Operator UI (`/ops`).
  - Unit 5: Public status page (`/status`).
  - Unit 6: Webhook notifications & reliability metrics.
  - Unit 7: Acceptance test drill and documentation.
- Known limitations:
  - Checks are not running on an async background loop yet (Unit 2).
