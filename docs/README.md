# Pulse — Service Status and Incident Hub

Pulse watches HTTP health endpoints, classifies service state, opens and resolves incidents automatically, notifies a webhook, and shows an operator dashboard and a read-only public status page.

> Draft. Finalise at Unit 7 after a fresh-clone run. Document only what works.

## Quick start (one command)
```
make up
```
- App: http://localhost:<APP_PORT>
- Operator dashboard: http://localhost:<APP_PORT>/ops
- Public status page: http://localhost:<APP_PORT>/status
- Health: http://localhost:<APP_PORT>/health

Requirements: Docker, Docker Compose, make. The supplied starter-kit services must be running on the same Docker network (see `docs/STARTER_KIT.md`).

## Configuration
Copy `.env.example` to `.env`. Keys: DB path, check timeout, degraded threshold, failure threshold, recovery threshold, webhook URL. Values come from `DECISIONS.md`.

## Tests
```
make test          # everything
make test U=02     # one unit
python scripts/acceptance.py   # full failure-to-recovery drill (< 90 s)
```

## Demo path
1. All four services healthy.
2. Trigger payments `/control/down`.
3. After the failure threshold: payments DOWN, one incident, timeline entry, webhook received.
4. Acknowledge the incident and add a note.
5. Trigger payments `/control/reset`.
6. After the recovery threshold: healthy, incident resolved, recovery webhook, public page updated.
7. Metrics show MTTD and MTTR.

## Working features
(fill from PROGRESS.md at Unit 7; only list what you verified)

## Limitations
- No authentication or roles (local demo).
- Availability and error-budget figures are estimates from periodic checks, not continuous monitoring.
- SQLite, single process.
- (add the rest honestly)

## Documents
- `PLAN.md` product plan · `ARCHITECTURE.md` design · `PROJECT_STRUCTURE.md` layout
- `DECISIONS.md` decisions · `REVIEW.md` self-assessment · `LOG.md` AI events
- `docs/` statement, questions, starter-kit recon, tests

## AI use (declared)
| Tool / model | Used for | Where (units) | Transcript |
|---|---|---|---|
| OpenCode + MiMo-V2.6-Pro | | | transcripts/ |
| OpenCode + DeepSeek V4.1 Flash | | | transcripts/ |
| NotebookLM / other chats | | | transcripts/prep/ |

I reviewed and can explain all code. Decisions in DECISIONS.md are my own.
