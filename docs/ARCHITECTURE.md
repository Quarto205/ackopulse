# ARCHITECTURE

Status: design draft. Every threshold and policy below comes from `DECISIONS.md`. Items marked **(D-?)** are not decided yet; do not code them until a D-entry exists.

## 1. Context

```
                      Docker Compose network
 ┌───────────────────────────────────────────────────────────────┐
 │  quotes   payments   claims   notifications   (mock services) │
 │      ▲        ▲        ▲          ▲                           │
 │      │        │        │          │   HTTP GET /health        │
 │      └────────┴────────┴──────────┘                           │
 │                       │                                       │
 │               ┌───────┴────────┐        POST event           │
 │               │  Pulse (app)   │ ───────────────────────►  webhook
 │               │  FastAPI       │                            receiver
 │               │  + SQLite file │                           (supplied)
 │               └───┬────────┬───┘
 └───────────────────┼────────┼──────────────────────────────────┘
                     │        │
              /ops (operator) /status (public)
                  browser       browser
```

Single process. One asyncio loop runs the web app, the scheduler and webhook sender tasks. No Redis, Celery or workers.

## 2. Components

| Component | Responsibility | Pure/IO | Unit |
|---|---|---|---|
| Config | Read env: DB path, timeout, thresholds, webhook URL | IO (startup) | U0 |
| Clock | `now()` in UTC, injectable in tests | pure | U1 |
| DB layer | aiosqlite, WAL, one write path, transactions | IO | U1 |
| Catalogue | Register/list services, validation | IO | U1 |
| Scheduler | Pick due services, run checks concurrently, update `next_check_at` | IO | U2 |
| Probe | One httpx request with timeout, returns result record | IO | U2 |
| Classifier | Result + counters -> new state, counters, incident action | **pure** | U3 |
| Incident store | Apply classifier output in one transaction, enforce one active incident | IO | U3 |
| Webhook sender | Background task, bounded retries, delivery records | IO | U6 |
| Metrics | Availability, budget, MTTD, MTTR, checker perf | **pure** | U6 |
| Operator UI | Server-rendered pages under `/ops` | IO | U4 |
| Public page | Server-rendered page under `/status`, own data model | IO | U5 |

Keep the classifier and metrics pure so the unit tests need no I/O.

## 3. Main flow (failure to recovery)

```
scheduler loop (every tick)
  └─ select services where next_check_at <= now and not currently running
       └─ for each, concurrently:  probe(service)  ── timeout bound ──►
            result {status, latency, error, scheduled_at, started_at, duration}
       └─ in ONE transaction per service:
            1. insert health_check row (with lag + duration)
            2. classify(result, counters) -> new state, counters, incident action
            3. update service (state, counters, first_failure_at, next_check_at)
            4. open / resolve incident + insert incident_event
            5. insert webhook_delivery row (pending) if event is opened/resolved
  └─ webhook sender (separate task) picks pending deliveries, POSTs, retries, records attempts
```

Rules that matter:
- Result, counters, state, incident and next_check_at are written in one transaction, so a crash cannot cause a double check or a half-applied transition.
- The webhook is never awaited inside the check path. Pending delivery rows make it restart-safe.
- One delivery per (incident, event) via a unique constraint, so a restart or race cannot duplicate it.
- One active incident per service via a partial unique index.

## 4. State model

States: `HEALTHY`, `DEGRADED`, `DOWN`.

Inputs: fast success, slow success, non-2xx, timeout, connection error, restart.

The rules (what counts as failed, degraded latency, failures to DOWN, recovery count, reopen behaviour) are defined only in `DECISIONS.md`. The full transition table lives in `docs/TESTS.md` under "State machine table". Every row has a test.

Open points to decide first: **(D-?)** failed-check definition and timeout, **(D-?)** degraded latency, **(D-?)** failures to DOWN, **(D-?)** recovery rule and whether a slow success counts, **(D-?)** reopen vs new incident, **(D-?)** whether DEGRADED opens an incident.

## 5. Data model

Starts from PLAN.md section 6, extended with what Units 1-6 need so no migration is required later.

**service**: id, name (unique), slug, health_url (unique), owner, interval_seconds, slo_target, enabled, current_state, consecutive_failures, consecutive_successes, first_failure_at, next_check_at, created_at

**health_check**: id, service_id, scheduled_at, started_at, checked_at, duration_ms, http_status (nullable), latency_ms (nullable), state, error_message (nullable)

**incident**: id, service_id, opened_at, resolved_at (nullable), status (active/resolved), acknowledged_at, acknowledged_by, title
- Partial unique index: one row per service where `status = 'active'`.

**incident_event**: id, incident_id, event_type (opened, acknowledged, note_added, resolved), message, created_at
- Operator notes are events; the timeline is the single source of truth.

**webhook_delivery**: id, incident_id, event_type, attempt, outcome, response_code, created_at, plus an idempotency key unique per (incident_id, event_type) for the logical event.

**checker_stats** (or derived): skipped runs counter, for "how the checking itself is performing".

All timestamps stored as UTC.

## 6. Interfaces

JSON API (from PLAN.md): `GET/POST /api/services`, `GET /api/services/{id}/checks`, `GET /api/incidents`, `POST /api/incidents/{id}/acknowledge`, `POST /api/incidents/{id}/notes`, `GET /api/metrics/summary`, `GET /api/public/status`.

UI routes: `/ops/...` for operators (dashboard, incident detail, add service form), `/status` for the public page.

State-changing actions are POST only. Operator and public routes use separate prefixes and separate data models.

Webhook: POST JSON to the receiver. Payload, auth and header names come from `docs/STARTER_KIT.md`. Events: opened, resolved (confirm in DECISIONS.md).

## 7. Security and privacy
- No authentication (out of scope; local demo). State this in README limitations.
- Public page shows only: service display name, status, incident title/start/end/status, recent history. It never shows health URL, owner, notes or acknowledge info **(confirm in D-?)**.
- All user-supplied text is HTML-escaped (Jinja2 autoescape on). A `<script>` note renders as text.
- No secrets in the repo. `.env.example` only; `make secrets-check` before push.

## 8. Reliability design
| Risk | Design response |
|---|---|
| Slow service blocks others | Concurrent checks, explicit timeout, one shared httpx client |
| Check pile-up when slower than interval | Skip service still running, count skipped runs |
| Drift / catch-up burst after stall | `next_check_at = scheduled time + interval`; no burst of catch-up checks |
| Double incident under concurrency | Partial unique index + single transaction |
| Duplicate webhook after restart | Pending delivery rows + unique (incident, event) |
| Receiver down | Bounded retries in background task; failure recorded; checking unaffected |
| SQLite lock contention | WAL, one write path **(D-?)** |
| Data lost on container recreate | DB file on a Docker volume |

## 9. Metrics (definitions to be fixed in DECISIONS.md)
- Availability over a rolling window, sampled from periodic checks (estimate, not continuous).
- Error budget remaining against the SLO target.
- MTTD: first failed check of the streak to incident opened.
- MTTR: incident opened to resolved.
- Checker performance: lag (actual start minus scheduled), duration, failed and skipped runs.
- No data shows "n/a", never 100%. Every uptime and budget figure carries the label "estimate from periodic checks".

Formulas stay **(D-?)** until you record them.

## 10. Testing approach
- Pure functions (classifier, metrics) get unit tests with no I/O.
- Integration tests use in-process fake HTTP servers and an injected clock; none depend on the real compose stack and none sleep more than 1 s.
- Acceptance script runs the full drill against the real stack, polls with timeouts, always resets payments in a `finally`, and finishes in under 90 s using short intervals from config.

## 11. Deployment
`make up` builds the app image and starts it on the same Docker network as the starter-kit services, exposing the app port. Config via environment. SQLite file on a volume.

## 12. Known decisions still open
| Topic | Needed before | Where to record |
|---|---|---|
| Frontend: Jinja2 server-rendered vs React (PLAN.md says React) | U0 | DECISIONS.md |
| DB access mode | U1 | DECISIONS.md |
| Failed check, timeout, degraded latency | U2 | DECISIONS.md |
| Failures to DOWN, recovery, reopen | U3 | DECISIONS.md |
| Ack/note rules | U3/U4 | DECISIONS.md |
| Public page privacy | U5 | DECISIONS.md |
| Webhook payload, retry, idempotency | U6 | DECISIONS.md + STARTER_KIT.md |
| Availability, budget, MTTD, MTTR formulas | U6 | DECISIONS.md |
