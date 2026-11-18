# PLAN.md — Pulse: Service Status and Incident Hub

## 1. Problem and users

**Chosen problem: Option 1 — Pulse.**

Pulse helps three groups:
- **Service owners / on-call engineers:** detect service failures quickly and manage incident response.
- **Support team:** understand which services are affected and whether an incident is ongoing.
- **Customers:** see a clear, read-only status page instead of guessing whether a failed payment or claim is caused by the platform.

The outcome that matters: detect service failures, track recovery, and communicate the current state to operators and customers.

## 2. Why Pulse

Pulse is the lower-risk choice for a six-hour solo build. The starter kit supplies four mock services (`quotes`, `payments`, `claims`, `notifications`), health endpoints, controls to simulate down/slow/flaky behaviour, a webhook receiver, and an incident drill script. The core product can therefore be demonstrated through real HTTP checks without building a container deployment system.

Launchpad requires image builds, registry pushes, container deployments, two environments, health validation, automatic rollback, manual rollback, and environment-specific configuration. That creates more integration risk within six hours.

## 3. Discovery: questions for the product owner

Ask these during the first 15 minutes. Record the actual answers here; do not invent answers.

| Question | Default if no answer is available |
|---|---|
| What response-time threshold separates healthy from degraded? | HTTP 2xx under 1.5 seconds is healthy; slower 2xx is degraded. |
| How many consecutive failures should open an incident? | Two consecutive failed checks; the first failure marks the service degraded. |
| How many successful checks are needed to resolve an incident? | Two consecutive healthy checks. |
| What availability window should the dashboard show? | Rolling 24 hours, labelled as a sampled estimate. |
| What SLO target should new services use? | 99.9%, editable per service. |
| What webhook payload or authentication does the supplied receiver expect? | Inspect its README and send the smallest compatible JSON payload. |
| Is it acceptable to extend the supplied Docker Compose setup? | Yes; keep the supplied mock services intact and add Pulse to the same runnable setup where practical. |

## 4. Similar-product research

Spend no more than five minutes reviewing the user-facing patterns of UptimeRobot, Better Stack, or Atlassian Statuspage. Record only patterns that directly inform this MVP:
- A service list with a clear current-state indicator.
- An incident history with opened, acknowledged, updated, and resolved events.
- A customer-facing status page separate from the operator controls.
- Availability and response-time measurements over a defined time window.

Do not copy their full feature scope. The six-hour build focuses on the end-to-end health-to-incident-to-recovery workflow.

## 5. MoSCoW scope

### Must have
- Service catalogue API and UI: name, health URL, owner, check interval, and SLO target.
- Independent periodic HTTP health checks; one slow service must not block checks for others.
- Persist each check result, including timestamp, HTTP status, latency, and classified state/error.
- Consistent `HEALTHY`, `DEGRADED`, and `DOWN` state transitions, including recovery.
- Automatically open an incident when a service becomes `DOWN`; resolve it after recovery.
- Incident acknowledgement, operator notes, and a chronological event timeline.
- Operator dashboard showing current states, latest response times, and active/recent incidents.
- Read-only public status page showing current state and recent incident history.
- One-command startup instructions and a README that documents the working features and limitations.

### Should have
- Webhook notification when an incident opens and when it resolves.
- Rolling 24-hour availability estimate, configured SLO, estimated error budget remaining, MTTD, and MTTR.
- Basic service and incident filters.

### Could have
- Small response-time history chart.
- Incident filtering by date and service.
- Edit/pause service monitoring.

### Won't have in this build
- Authentication, roles, and customer subscriptions.
- AI-generated incident summaries.
- Email/SMS integrations, Kubernetes, non-HTTP probes, or complex alert routing.
- Distributed workers, Redis, Celery, or a separate monitoring stack.

If time is short, finish the core workflow first. Keep notifications and metrics simple rather than sacrificing detection, incident tracking, or recovery.

## 6. System design

### Proposed architecture

```text
Mock services (quotes, payments, claims, notifications)
              ^
              | asynchronous HTTP health checks
              |
       FastAPI backend
       |      |       |
   Scheduler State  Incident + webhook logic
       |      |       |
       +--- SQLite database
              |
        REST API endpoints
              |
        React dashboard
          /        \
 Operator view   Public status page
```

### Technology choices
- **Backend:** Python + FastAPI.
- **Health probes:** `httpx` asynchronous client with per-request timeouts and concurrent checks.
- **Scheduling:** one lightweight `asyncio` background loop that selects services due for a check. Avoid Celery/Redis.
- **Database:** SQLite for the six-hour MVP.
- **Frontend:** React + Vite; keep styling simple and prioritize readable status and incident information.
- **Runtime:** Docker Compose, reusing the provided mock services and webhook receiver.

### State rules (initial defaults; update if the product owner specifies otherwise)
- HTTP 2xx with latency below 1.5 seconds: `HEALTHY`.
- HTTP 2xx with latency at or above 1.5 seconds: `DEGRADED`.
- First timeout/non-2xx result: `DEGRADED`.
- Two consecutive timeout/non-2xx results: `DOWN`; open one active incident if one does not already exist.
- Two consecutive healthy results after `DOWN`: `HEALTHY`; resolve the active incident and emit a recovery event.
- A slow but successful result remains `DEGRADED`; it does not count as a healthy recovery result.
- Run checks concurrently and apply a timeout so a slow dependency cannot stall other services.

### Initial data model

- **Service:** `id`, `name`, `slug`, `health_url`, `owner`, `interval_seconds`, `slo_target`, `enabled`, `current_state`, `created_at`.
- **HealthCheck:** `id`, `service_id`, `checked_at`, `http_status`, `latency_ms`, `state`, `error_message`.
- **Incident:** `id`, `service_id`, `opened_at`, `resolved_at`, `status`, `acknowledged_at`, `acknowledged_by`.
- **IncidentEvent:** `id`, `incident_id`, `event_type`, `message`, `created_at`.

Store operator notes as incident events so the timeline is the single source of truth for incident activity.

### API sketch

- `GET /api/services` — list monitored services.
- `POST /api/services` — register a service.
- `GET /api/services/{id}/checks` — recent check history.
- `GET /api/incidents` — list active/recent incidents.
- `POST /api/incidents/{id}/acknowledge` — acknowledge an incident.
- `POST /api/incidents/{id}/notes` — append an operator note.
- `GET /api/metrics/summary` — availability and incident metrics.
- `GET /api/public/status` — public-safe service state and recent incident history.

## 7. Main screens

1. **Operator dashboard:** summary counts, service table, state, last check, latency, SLO, and active incidents.
2. **Incident detail:** status, service, opened/resolved times, acknowledgement, notes, and event timeline.
3. **Public status page:** service names, current state, and recent incident history; no operator controls.
4. **Add service form:** name, health URL, owner, interval, and SLO target.

## 8. Six-hour execution plan

| Time | Unit / work | Exit condition |
|---|---|---|
| 0:00–0:15 | Choose Pulse, create public Git repository, inspect and start the supplied starter kit, identify ports and webhook behaviour. | Mock services and controls are reachable; repo exists. |
| 0:15–1:15 | Discovery and Gate 1: ask product-owner questions, inspect one or two similar products, settle assumptions, write this `PLAN.md`, sketch schema/screens, and define tests/metrics. | `PLAN.md` committed by 1:15. |
| 1:15–1:45 | Unit 1 — Backend and database bootstrap: FastAPI app, SQLite connection, schema, seed four services. | API starts and `GET /api/services` returns seeded services. |
| 1:45–2:30 | Unit 2 — Health-check engine: async HTTP checks, per-service interval, timeout, latency capture, persistence. | Every service is checked independently and results appear in the database. |
| 2:30–3:15 | Unit 3 — State and incident engine: classification, consecutive-failure/recovery rules, incident open/resolve, event timeline, acknowledge and notes endpoints. | Simulated failure opens one incident; reset and recovery resolve it. |
| 3:15–3:30 | Integration checkpoint and Gate 2: smoke-test the end-to-end backend, commit, write `PROGRESS.md` with what works and what remains. | Gate 2 progress note and working backend committed by 3:30. |
| 3:30–4:15 | Unit 4 — Operator UI: service dashboard, latest checks, incident list, incident detail, acknowledge and add-note actions. | Operator can see and manage an incident in the browser. |
| 4:15–4:40 | Unit 5 — Public status page: read-only current service states and recent incident history. | Public page updates after a simulated failure/recovery. |
| 4:40–5:10 | Unit 6 — Notifications and metrics: webhook on open/resolve; 24-hour sampled availability, SLO/error-budget estimate, MTTD and MTTR. | Webhook receiver shows events; metrics render with clear labels. |
| 5:10–5:30 | Unit 7 — Verification and bug fixing: run unit/integration/acceptance tests and the complete demo path. | No known blocker in the primary demo workflow. |
| 5:30–6:00 | Finalize README, `DECISIONS.md`, `REVIEW.md`, transcripts, final commit, and demo rehearsal. | Fresh-start instructions work; all required files are committed before the deadline. |

**Commit discipline:** commit at least every 45 minutes during the build. Suggested checkpoints: 2:00, 2:45, 3:30, 4:15, 5:00, and 5:45. Never leave the first working end-to-end path uncommitted.

## 9. Unit-wise implementation checklist

### Unit 1 — Backend and database
- [ ] FastAPI app starts.
- [ ] SQLite tables are created automatically.
- [ ] Seed the four supplied mock services.
- [ ] Service list and registration endpoints work.

### Unit 2 — Health-check engine
- [ ] Find services whose next check is due.
- [ ] Run due checks concurrently with `httpx.AsyncClient`.
- [ ] Apply a timeout and capture status code, latency, timestamp, and error.
- [ ] Persist every result and update each service's next-check time.

### Unit 3 — State and incident engine
- [ ] Unit-test state classification and consecutive-failure/recovery rules.
- [ ] Open only one active incident per service.
- [ ] Record opened, acknowledged, note-added, and resolved events.
- [ ] Resolve an incident only after the configured recovery condition.

### Unit 4 — Operator UI
- [ ] Display service state and last response time.
- [ ] Display active and recent incidents.
- [ ] Show an incident timeline.
- [ ] Provide acknowledge and add-note actions.

### Unit 5 — Public status page
- [ ] Show service status and recent incidents.
- [ ] Keep the page read-only and do not expose operator actions.

### Unit 6 — Notifications and metrics
- [ ] POST webhook event when an incident opens.
- [ ] POST webhook event when an incident resolves.
- [ ] Show rolling 24-hour sampled availability and target SLO.
- [ ] Show estimated error budget remaining, MTTD, and MTTR.
- [ ] Label uptime/error-budget figures as estimates derived from periodic checks, not continuous packet-level monitoring.

### Unit 7 — Verification and handover
- [ ] Unit tests for classification, transitions, incident uniqueness, and metric calculations.
- [ ] Integration test for health check persistence and incident lifecycle.
- [ ] Acceptance test for the full failure-to-recovery flow.
- [ ] Verify the README startup steps on a clean run.
- [ ] Save AI coding transcripts in `transcripts/`.
- [ ] Write `DECISIONS.md` and `REVIEW.md`.

## 10. Test plan and success metrics

### Unit tests
- Healthy, degraded, and failed response classification.
- Consecutive failure and recovery thresholds.
- No duplicate active incidents for one service.
- Availability, MTTD, MTTR, and error-budget calculations.

### Integration tests
- Health check calls a mock `/health` endpoint and persists the result.
- A down service opens an incident and sends a webhook.
- A recovered service resolves the incident and sends a recovery webhook.
- A slow service does not block checks for other services.

### Acceptance test
1. Start the complete application and supplied mock services.
2. Confirm all four services initially show healthy.
3. Trigger the Payments service `/control/down` endpoint.
4. Wait for the configured failure threshold; confirm `DOWN`, an open incident, timeline entry, and webhook notification.
5. Acknowledge the incident and add a note.
6. Trigger `/control/reset`.
7. Wait for the recovery threshold; confirm `HEALTHY`, resolved incident, recovery event, and updated public status page.

### Product metrics
- Detection delay / MTTD.
- Mean time to recovery / MTTR.
- Sampled availability over the rolling 24-hour window versus the service SLO.
- Mean/latest health-check response time and failed-check count.
- Webhook delivery success/failure count.

## 11. Explicit assumptions and risks

- The supplied starter kit and mock services are available and can be run locally.
- The MVP uses periodic HTTP probes; availability and error-budget values are sampled estimates.
- SQLite is sufficient for a local single-operator demo.
- No authentication is included; the operator dashboard is for the local demo only.
- If frontend work takes longer than expected, keep the public page minimal and finish incident lifecycle, webhook, tests, and runnable setup first.
- Do not introduce Redis, Celery, Kubernetes, or a separate observability stack during the hackathon.

## 12. Demo script

Show the dashboard with all four services healthy. Trigger the Payments mock service's down control. Show Pulse detect the failure, change the state, open an incident, and send a webhook. Acknowledge the incident and add an operator note. Reset Payments. Show Pulse detect recovery, resolve the incident, and update the public page and metrics.

The demo is successful when the failure-to-recovery lifecycle works end to end without manually editing the database or refreshing service state by hand.
