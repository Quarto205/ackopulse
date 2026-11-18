# PULSE UNIT PROMPTS: your 7-unit plan, ready to paste (3-hour build)

Stack from your plan: FastAPI, SQLite, httpx.AsyncClient. Tags: **PRO** = MiMo-V2.6-Pro, **FLASH** = DeepSeek V4.1 Flash. Mode in OpenCode: **Plan** (read-only) or **Build** (writes).
Every prompt reads repo files, takes at most one blank, and makes the AI execute, check or flag. It never decides a threshold or policy for you.

## 0. How to run a unit
1. `bash scripts/unit-start.sh NN name` (new branch). Open a new OpenCode session; first prompt is **S** (section 3).
2. **K** (kickoff + tests first). It stops if a decision is missing. Answer with section 2's proposals, log with prompt **LOG**, then reply `go`.
3. **I** (implement). 4. **R** (review, Plan mode). 5. **CLOSE**. 6. Commit, then `bash scripts/unit-done.sh NN name`. 7. `opencode export` into `transcripts/`.
Going badly (same test fails twice for the same cause): **DBG**. Over 1.5x the estimate: **CUT**. Past 2x: `bash scripts/unit-rollback.sh NN name`, log `ROLLBACK`, move on.

| Unit | Est. min | Must-haves | Model for K and I |
|---|---|---|---|
| U0 wiring (added) | 8 | 10 | FLASH |
| U1 Backend + DB | 12 | 1 | FLASH |
| U2 Health-check engine | 18 | 2, 9 | PRO |
| U3 State + incident engine | 18 | 3, 4 | PRO |
| U4 Operator UI | 14 | 1, 4, 6 | FLASH |
| U5 Public status page | 8 | 7 | FLASH |
| U6 Notifications + metrics | 18 | 5, 8, 9 | FLASH (fixtures: PRO) |
| U7 Verification + handover | 16 | 10 | PRO |
| **Total** | **112** | | |

112 minutes is over a ~100-minute build window. Plan to use CUT on U4 or U5, never to drop a must-have.

## 1. Gaps in your plan, and where I put the fixes
Items marked **ADDED** are in the unit prompts below. Delete a line from a prompt if you disagree.

| Gap | Statement | Where fixed |
|---|---|---|
| Registration is API only; no UI to register a service | #1 "API and a UI" | **ADDED** to U4 (thin form) |
| Dashboard shows only the last response time | #6 "recent response times" | **ADDED** to U4 (last N per service) |
| Public page shows incidents only, no per-service history | #7 "recent history of each service" | **ADDED** to U5 |
| Nothing measures the checker itself | #9 "how the checking itself is performing" | **ADDED**: store lag + duration in U2, show in U6 |
| Nothing makes it one-command runnable until U7 | #10 | **ADDED** U0 wiring |
| No webhook delivery records, no restart safety | #8, #2 | **ADDED** to U2, U3, U6 tests |
| Thresholds and policies are "configured" but undecided | #3, #8 | Decision sheet, section 2 |

## 2. Decision sheet: PROPOSED defaults
These are proposals, not decisions. The statement says "Don't hand it your decisions" and the panel will ask you to defend each one. For each row: accept or change, ask the PO where it is a PO question, then log it with prompt **LOG** in your own words with your own reason.

| # | Topic | Proposed default | Reason |
|---|---|---|---|
| T1 | DB access | SQLite via aiosqlite, WAL mode, one write path | async loop must not block; WAL avoids reader/writer locks |
| T2 | Failed check and timeout | Non-2xx, timeout (5 s) or connection error = failed | mock `slow?ms=3000` then counts as slow, not failed |
| T3 | Degraded latency | Success slower than 1000 ms = DEGRADED | separates normal from the 3000 ms slow control |
| T4 | Failures to DOWN | 3 consecutive failed checks | one blip or flaky 30% won't open an incident easily |
| T5 | Recovery | 2 consecutive successes (2xx in time) resolve the incident; state then HEALTHY/DEGRADED by latency. A slow success counts as success | simple and testable |
| T6 | Flapping / reopen | DEGRADED never opens an incident. After resolve, a new DOWN opens a new incident (no reopen) | fewer states |
| T7 | Scheduling | Interval 10 s default, 5 s to 3600 s allowed. `next_check_at = scheduled time + interval`. A service still being checked is skipped and counted | no drift, no pile-up |
| T8 | Registration validation | http/https URL, unique name and URL, interval in bounds, target 90 to 100 (%) | clear 4xx errors |
| T9 | Time | Store UTC, display UTC (labelled). Injected clock function and config-driven intervals so tests run in seconds | testability |
| T10 | UI approach | Server-rendered Jinja2 pages, meta-refresh every 5 s, no JS build | one-command run, less to break |
| T11 | Ack and notes | Ack sets an acknowledged flag and event, does not resolve; notes allowed on active incidents; resolved incidents reject ack | clear rules |
| T12 | Public page privacy | Show service display name, status, incident title/start/end/status and last N checks as a status strip. Hide health URL, owner, notes, ack info | customers don't need internals |
| T13 | Webhook | Events: opened, resolved only. Payload shape from `docs/STARTER_KIT.md`. Retry 3 times with 2 s backoff in a background task. Every attempt is a delivery record. One delivery per (incident, event) | no duplicates after restart |
| T14 | Availability and budget | Count-based over rolling 24 h: good checks (healthy or degraded) / all checks. Budget = (1 - target) x checks in window; remaining = budget - failed checks. MTTD = first failed check of the streak to incident opened. MTTR = incident opened to resolved. Averages over resolved incidents in the window. No data shows "n/a". All figures labelled "estimate from periodic checks" | matches your plan's "sampled" wording |
| T15 | Checker performance | Per check: lag (actual start minus scheduled) and duration; show average lag, average duration and failed/skipped runs over 24 h | what "how the checking itself is performing" most plausibly means; confirm with PO |
| T16 | Seed data | Targets 99.5% for the four seeded services, owner = team name text, interval 10 s | demo-able |

## 3. Anytime prompts

**S: session start** `[FLASH, Plan]`
```
Read AGENTS.md, PROGRESS.md and DECISIONS.md only. Reply in ≤6 lines: current unit, its acceptance criteria, last 3 decisions, next action. No code.
```

**LOG: record a decision or PO answer** `[FLASH, Build]` (1 blank)
```
Append to DECISIONS.md, timestamped from `date`, verbatim: "[D-nn: my decision, alternatives, my reason, origin]". Then list conflicts with earlier entries, IDs only. Edit nothing else.
```

**DBG: debug as second brain** `[PRO, Plan]` (3 blanks)
```
Symptom: [..]. Expected: [..]. My hypothesis: [..]. Give 3 ranked hypotheses including mine, each with the cheapest check that confirms or kills it. Don't edit code.
```

**CUT: unit over budget** `[PRO, Plan]` (1 blank)
```
Unit [N] is past 1.5x its estimate. Read PLAN.md and DECISIONS.md. List 2-3 ways to shrink it that keep every must-have #1-#10 present in thin form: minutes saved, what the demo loses, which tests drop. No recommendation. I'll decide and log it.
```

**CLOSE: close-out (after R)** `[FLASH, Build]` (1 blank)
```
Close Unit [NN]: update PROGRESS.md (status, test counts, branch), docs/TESTS.md (test case rows and last run), LOG.md (a tag for every AI error or rejected suggestion this unit). Give files changed and a commit message. Don't commit.
```

**QUIZ: explain-back** `[PRO, Plan]` (0 blanks, run for U2, U3, U6 at least)
```
Quiz me on this unit's diff, one question at a time: why this approach, what breaks if X changes, how test T proves criterion C. Wait for my answer, then say exactly what I got wrong. 3 questions, then list my weakest areas.
```

## 4. Pre-flight (before Unit 0, about 10 min)

**Save the starter-kit recon.** Run prompt A2 from the 3-hour kit, then save its output as `docs/STARTER_KIT.md` (ports, hostnames on the Compose network, endpoints, webhook payload and auth, drill schedule). Units 0, 1 and 6 read this file.

**PF1: gap check on my plan** `[PRO, Plan]`
```
Read docs/STATEMENT.md and PLAN.md sections 4, 9 and 10. Violations only: (1) must-haves #1-#10 not covered by any unit, or only partly (name the missing part); (2) a unit not testable alone or not demoable; (3) tests in section 10 that no unit builds; (4) decisions the plan relies on that DECISIONS.md lacks: thresholds, timeouts, webhook retry, public-page privacy, availability, MTTD and MTTR definitions. Don't edit.
```

**PF2: decision menu for what's still open** `[PRO, Plan]`
```
Read DECISIONS.md and docs/QUESTIONS.md. For each topic not yet decided: database access from async code, failed-check definition and timeout, degraded latency, failures to DOWN, recovery rule, reopen vs new incident, scheduling and overlap, registration validation, time handling, UI approach, acknowledge and note rules, public page privacy and history, webhook payload/retry/idempotency, availability/error-budget/MTTD/MTTR definitions, checker performance metrics: give 2-3 options, one line each on minutes, what's hard to test, how it fails. No recommendation. ≤40 lines.
```

---

## UNIT 0: Wiring (added, about 8 min, FLASH)
Needs: stack (given), T9 (clock config). Branch: `bash scripts/unit-start.sh 00 wiring`. Demo: `make up` shows the app's `/health` next to the starter kit.

**0.1 Build** `[FLASH, Build]`
```
Read DECISIONS.md and docs/STARTER_KIT.md. Create only: a FastAPI app skeleton with GET /health; pytest config with one passing test and markers unit_00 to unit_07 so `make test U=<nn>` runs `pytest -m unit_<nn>`; a Dockerfile; compose wiring that runs the app on the same Docker network as the starter-kit services and exposes the app port; Makefile targets `up`, `test`, `test U=<nn>` replacing the stubs; .env.example entries for config (DB path, check timeout, degraded threshold, failure and recovery thresholds, webhook URL). Ports and hostnames only from docs/STARTER_KIT.md; if missing, stop and tell me. Nothing else.
```
Then **CLOSE**, commit, `bash scripts/unit-done.sh 00 wiring`.

---

## UNIT 1: Backend and database (about 12 min, FLASH)
Needs: T1, T8, T16. Branch: `bash scripts/unit-start.sh 01 backend-db`. Demo: `curl` the service list and see the four seeded services; register a fifth.

**1.1 Kickoff + tests first** `[FLASH, Build]`
```
Unit 1: backend and database. Read PROGRESS.md, DECISIONS.md and docs/STARTER_KIT.md.
My scope: FastAPI app starts; SQLite tables created automatically; the four supplied mock services seeded; service list and registration endpoints work. ADDED: the schema must hold what later units need without a migration: per-service interval, owner, reliability target, next_check_at, current state, consecutive failure and success counters, first-failure timestamp.
Step 1: in ≤4 lines restate the acceptance criteria and list the files you will create or change.
Step 2: flag anything DECISIONS.md doesn't cover (DB access mode, registration validation rules, interval and target bounds, duplicate handling, seed values). If any is uncovered, stop and list 2-3 options with minutes and test impact, no recommendation.
Step 3: otherwise write failing tests only, marker unit_01: app starts and /health is ok; tables created on an empty DB; restart keeps data; seed inserts exactly 4 services and running seed twice still gives 4; seeded health URLs match docs/STARTER_KIT.md; list returns all; registering a valid service returns it and it appears in the list; invalid URL, missing field, interval or target out of bounds, duplicate name, duplicate URL each rejected with a clear 4xx; schema has the counter, state, next_check_at and first-failure columns. Run them and show they fail for the right reason, not import errors. Stop and wait for "go".
```

**1.2 Implement** `[FLASH, Build]`
```
go. Implement the minimum to pass. DB access exactly as in DECISIONS.md, no extra libraries beyond it. Run unit_01 tests, then the full suite. If the same test fails twice for the same cause, stop and show me, no third attempt. Don't touch files outside your list.
```

**1.3 Review** `[PRO, Plan]`
```
Review git diff main...HEAD against PLAN.md and DECISIONS.md. Max 8 by severity. Check specifically: seed not idempotent across restarts; DB file not on a volume so data vanishes on container recreate; table-creation race at startup; validation accepting non-http URLs or blank names; the list/response model exposing fields a public page must never get (owner, health URL); timestamps naive or not UTC. Then 3 lines per changed file (what and why) so I can check I can explain it. Don't edit code.
```
Then **CLOSE** `01`, commit, `bash scripts/unit-done.sh 01 backend-db`.
Viva questions to expect: why WAL and a single write path? What stops the seed running twice? Where do the counters live and why?

---

## UNIT 2: Health-check engine (about 18 min, PRO)
Needs: T1, T2, T7, T9, T15. Branch: `bash scripts/unit-start.sh 02 health-checks`. Demo: start the app, watch result rows appear for four services; stop one mock service and see error rows.

**2.1 Kickoff + tests first** `[PRO, Build]`
```
Unit 2: health-check engine. Read PROGRESS.md, DECISIONS.md and PLAN.md Unit 2 only.
My scope: find services whose next check is due; run due checks concurrently with httpx.AsyncClient; apply a timeout and capture status code, latency, timestamp and error; persist every result and update each service's next-check time. ADDED: store lag (actual start minus scheduled time) and duration per check, and count skipped runs, so product metrics can show how the checking itself performs.
Step 1: restate the acceptance criteria in ≤4 lines and list the files you'll create or change.
Step 2: flag anything DECISIONS.md doesn't cover: failed-check definition, timeout, next_check_at rule, overlap handling, clock injection, DB write path. If any is uncovered, stop and list 2-3 options with minutes and test impact, no recommendation.
Step 3: otherwise write failing tests only, marker unit_02, using in-process fake HTTP servers (not the real compose stack) and an injected clock: only due services are selected (due, not due, exactly due); 4 services where one sleeps longer than the others: total time is about the slowest, and fast services' results are persisted before the slow one finishes; slower than the timeout gives a persisted row with an error and no status code; 500 persists its status code; connection refused persists an error; every row has service id, timestamp, status code, latency, error, scheduled time, started time, duration; next_check_at is updated after each run per the decided rule and a long stall doesn't cause a burst of catch-up checks; a service whose previous check is still running is skipped and counted; restart with overdue next_check_at runs each service once, not repeatedly; an exception in one check doesn't stop the others; tests never sleep more than 1 s. Run them and show they fail for the right reason. Stop and wait for "go".
```

**2.2 Implement** `[PRO, Build]`
```
go. Implement the minimum to pass: a scheduler loop started in the app lifespan, one shared httpx.AsyncClient with an explicit timeout, due-service selection, concurrent execution, one persistence path for results and next_check_at in a single transaction. No state classification or incidents here (Unit 3). Run unit_02 tests, then the full suite. If the same test fails twice for the same cause, stop and show me, no third attempt. Don't touch files outside your list.
```

**2.3 Review** `[PRO, Plan]`
```
Review git diff main...HEAD against PLAN.md and DECISIONS.md. Max 8 by severity. Check specifically: a shared SQLite connection used from concurrent tasks; blocking calls inside the event loop; result written but next_check_at not updated in the same transaction (double check after a crash); unbounded task growth when checks run slower than the interval; next_check_at drift; swallowed exceptions; an httpx client created per request; timeout not covering connect and read; datetime.now used instead of the injected clock; naive timestamps. Then 3 lines per changed file (what and why). Don't edit code.
```
Then **CLOSE** `02`, **QUIZ**, commit, `bash scripts/unit-done.sh 02 health-checks`.
Viva questions to expect: how does one slow service not block the others? What happens to next_check_at after a restart? Why is the write in one transaction?

---

## UNIT 3: State and incident engine (about 18 min, PRO)
Needs: T4, T5, T6, T11 and T2/T3. Branch: `bash scripts/unit-start.sh 03 state-incidents`. Demo: feed a fake failure streak and see one incident with a timeline; feed successes and see it resolve.

**3.0 State machine table first** `[PRO, Plan]` (highest-value prompt; the table doubles as your viva material)
```
Read DECISIONS.md. Use only thresholds and transition rules recorded there; if one is missing, write MISSING, don't invent it.
Produce a full table: current state (HEALTHY, DEGRADED, DOWN) × event (fast success, slow success, non-2xx, timeout, connection error, Pulse restart) → next state, counters after, incident action, event logged. Include unlisted combinations: DOWN + one slow success, DOWN + one healthy, failures just under the threshold, fail/success flapping, new DOWN soon after a resolve, the 30% flaky service. Mark rows my rules don't determine OPEN. Then one test case per row. No implementation. Write it to docs/TESTS.md under "State machine table" only if I say so.
```

**3.1 Kickoff + tests first** `[PRO, Build]`
```
Unit 3: state and incident engine. Read PROGRESS.md, DECISIONS.md, PLAN.md Unit 3 only and the state machine table in docs/TESTS.md.
My scope: unit-test state classification and consecutive-failure/recovery rules; open only one active incident per service; record opened, acknowledged, note-added and resolved events; resolve an incident only after the configured recovery condition.
Step 1: restate the acceptance criteria in ≤4 lines and list the files you'll create or change.
Step 2: flag anything DECISIONS.md doesn't cover: how this engine is triggered after each result, how notifications will hook in later (don't build them), acknowledge and note rules, behaviour on resolved incidents. If any is uncovered, stop and list 2-3 options with minutes and test impact, no recommendation.
Step 3: otherwise write failing tests only, marker unit_03: classification (fast 2xx is healthy, slow 2xx degraded, non-2xx / timeout / error is failure); threshold boundary (n-1 failures not DOWN, n failures DOWN); a success resets the failure counter; exactly one incident opens at the DOWN transition and further failures add none; a DB-level guard stops two active incidents for one service even under two concurrent evaluations; events opened, acknowledged, note_added, resolved each have a timestamp and an order; acknowledging twice is idempotent; notes append in order; k-1 successes leave the incident active, k resolve it; DOWN + one slow success and DOWN + one healthy follow the decided rule; flapping below the threshold opens nothing; a new failure streak after a resolve opens a new incident; first_failure_at is set at the start of a streak and cleared after recovery; restart mid-incident reloads counters and the active incident with no duplicate; acknowledging a resolved incident is rejected per the decision; every row of the state machine table has a matching test. Run them and show they fail for the right reason. Stop and wait for "go".
```

**3.2 Implement** `[PRO, Build]`
```
go. Implement the minimum to pass: a pure function for classification and transitions with no I/O, plus a thin persistence layer that updates counters, state, incident and events in one transaction, with a partial unique index so only one incident per service can be active. Do not write any webhook code. Run unit_03 tests, then the full suite. If the same test fails twice for the same cause, stop and show me, no third attempt. Don't touch files outside your list.
```

**3.3 Review** `[PRO, Plan]`
```
Review git diff main...HEAD against PLAN.md and DECISIONS.md and the state machine table. Max 8 by severity. Check specifically: counters updated outside the transaction; two incidents created under concurrent evaluation; incident resolved while the service state stays DOWN; recovery condition miscounted after a restart; events written out of order or missing a timestamp; acknowledge allowed on a resolved incident; DEGRADED flapping spamming events; any table row with no test. Then 3 lines per changed file (what and why). Don't edit code.
```
Then **CLOSE** `03`, **QUIZ**, commit, `bash scripts/unit-done.sh 03 state-incidents`.
Viva questions to expect: walk me through DOWN + a slow success. How do you guarantee one active incident? What survives a restart?

---

## UNIT 4: Operator UI (about 14 min, FLASH)
Needs: T10, T11. Branch: `bash scripts/unit-start.sh 04 operator-ui`. Demo: dashboard on screen, trigger `/control/down` on payments, acknowledge and add a note.

**4.1 Kickoff + tests first** `[FLASH, Build]`
```
Unit 4: operator UI. Read PROGRESS.md, DECISIONS.md and PLAN.md Unit 4 only.
My scope: display service state and last response time; display active and recent incidents; show an incident timeline; provide acknowledge and add-note actions. ADDED: show the last N response times per service (statement #6 "recent response times"); a thin service registration form (statement #1 "API and a UI"); empty states.
Step 1: restate the acceptance criteria in ≤4 lines and list the files you'll create or change.
Step 2: flag anything DECISIONS.md doesn't cover: UI approach, refresh method, N for recent response times, URL layout separating operator routes from public ones, time display. If any is uncovered, stop and list 2-3 options with minutes and test impact, no recommendation.
Step 3: otherwise write failing tests only, marker unit_04: dashboard returns 200 with every service, its state and last response time; recent response times appear in time order; active incidents are listed before resolved ones; incident detail shows the timeline events in order; acknowledge changes the incident and adds an event; add-note appends a note; an empty note is rejected; notes and service names are HTML-escaped (a <script> note renders as text); acknowledging a resolved incident is rejected; unknown incident id returns 404; double submit of acknowledge adds no second event; registration form creates a service that then appears; invalid registration shows an error and creates nothing; no-incident and no-check states render without errors; operator routes live under a prefix the public page won't use. Run them and show they fail for the right reason. Stop and wait for "go".
```

**4.2 Implement** `[FLASH, Build]`
```
go. Implement the minimum to pass, using the UI approach in DECISIONS.md. Reuse Unit 3's functions for acknowledge and notes, no duplicated logic. Run unit_04 tests, then the full suite. If the same test fails twice for the same cause, stop and show me, no third attempt. Don't touch files outside your list.
```

**4.3 Review** `[PRO, Plan]`
```
Review git diff main...HEAD against PLAN.md and DECISIONS.md. Max 8 by severity. Check specifically: unescaped notes or service names (XSS); state-changing actions reachable by GET; N+1 queries on the dashboard; operator-only data exposed on a route the public page might share; timeline time zone shown inconsistently; business logic duplicated from Unit 3. Then 3 lines per changed file (what and why). Don't edit code.
```
Then **CLOSE** `04`, commit, `bash scripts/unit-done.sh 04 operator-ui`.
Viva questions to expect: why server-rendered? What stops a note from running script? What happens with no login on acknowledge?

---

## UNIT 5: Public status page (about 8 min, FLASH)
Needs: T12. Branch: `bash scripts/unit-start.sh 05 public-page`. Demo: open `/status` in a private window while payments is down.

**5.1 Kickoff + tests first** `[FLASH, Build]`
```
Unit 5: public status page. Read PROGRESS.md, DECISIONS.md and PLAN.md Unit 5 only.
My scope: show service status and recent incidents; keep the page read-only and do not expose operator actions. ADDED: recent history per service (statement #7).
Step 1: restate the acceptance criteria in ≤3 lines and list the files you'll create or change.
Step 2: flag anything DECISIONS.md doesn't cover: which fields customers may see, the history shape, wording. If uncovered, stop and list 2-3 options with minutes and test impact, no recommendation.
Step 3: otherwise write failing tests only, marker unit_05: the page returns 200 with each service and its status in customer-friendly wording; a service going DOWN changes the page; recent incidents show title, start, end and status; health URLs, owners, operator notes and acknowledge info never appear anywhere in the HTML; the page contains no forms, buttons or links to operator routes; POST, PUT and DELETE on the public route return 405; no incidents and no checks both render; recent history per service renders in time order; HTML-escaped output. Run them and show they fail for the right reason. Stop and wait for "go".
```

**5.2 Implement** `[FLASH, Build]`
```
go. Implement the minimum to pass using a dedicated public data model that contains only the allowed fields, never the operator model. Run unit_05 tests, then the full suite. If the same test fails twice for the same cause, stop and show me, no third attempt. Don't touch files outside your list.
```

**5.3 Review** `[PRO, Plan]`
```
Review git diff main...HEAD against PLAN.md and DECISIONS.md. Max 6 by severity. Check specifically: a shared template or serializer leaking owner, health URL or notes; any operator route linked or reachable from the public page; stale caching hiding a DOWN; unescaped output. Then 3 lines per changed file. Don't edit code.
```
Then **CLOSE** `05`, commit, `bash scripts/unit-done.sh 05 public-page`.
Viva questions to expect: what exactly can a customer see and why? How is the public model kept separate?

---

## UNIT 6: Notifications and metrics (about 18 min, FLASH; fixtures PRO)
Needs: T13, T14, T15. Branch: `bash scripts/unit-start.sh 06 notify-metrics`. Demo: webhook receiver page shows the open and resolve events; dashboard shows availability, budget, MTTD, MTTR with the "estimate" label.

**6.0 Metric fixtures first** `[PRO, Plan]`
```
Read DECISIONS.md. For availability over a rolling 24 h window, error budget remaining, MTTD, MTTR and checker performance (average lag, average duration, failed and skipped runs), create 1 small fixture dataset (checks with timestamps, states, one incident, one resolved incident) and compute every expected value by hand, showing arithmetic. Include a no-data case, a window-boundary case (a check exactly 24 h old) and a case where the budget is exhausted. Say which definition is ambiguous on which input. Don't change my formulas. Output only; I'll save it to docs/TESTS.md.
```

**6.1 Kickoff + tests first** `[FLASH, Build]`
```
Unit 6: notifications and metrics. Read PROGRESS.md, DECISIONS.md, docs/STARTER_KIT.md, PLAN.md Unit 6 only and the metric fixtures in docs/TESTS.md.
My scope: POST a webhook event when an incident opens and when it resolves; show rolling 24-hour sampled availability and the target SLO; show estimated error budget remaining, MTTD and MTTR; label uptime and error-budget figures as estimates derived from periodic checks, not continuous monitoring. ADDED: webhook delivery records and success rate; checker performance (average lag, average duration, failed and skipped runs) so statement #9 is covered.
Step 1: restate the acceptance criteria in ≤4 lines and list the files you'll create or change.
Step 2: flag anything DECISIONS.md doesn't cover: webhook payload and auth (from docs/STARTER_KIT.md), retry policy, idempotency key, which events notify, how Unit 3 triggers notifications, availability and budget formulas, MTTD/MTTR definitions, display of no data and of an exhausted budget. If any is uncovered, stop and list 2-3 options with minutes and test impact, no recommendation.
Step 3: otherwise write failing tests only, marker unit_06, with a fake receiver: opening an incident POSTs exactly one event with the decided payload; resolving POSTs exactly one; each attempt is stored as a delivery record (event, attempt, outcome, response code, time); receiver down triggers the decided retries, the failure is recorded, and health checking continues unblocked; after a restart, delivered events are not re-sent and undelivered ones follow the decided rule; the same (incident, event) is never delivered twice; acknowledging or adding a note sends nothing unless decided; payload carries no operator notes unless decided; availability, error budget, MTTD, MTTR and checker performance equal the hand-computed fixture values; no data shows "n/a", never 100%; the budget exhausted case shows 0 remaining; a check exactly at the window boundary follows the fixture; the UI text contains the "estimate from periodic checks" label next to every uptime and budget figure. Run them and show they fail for the right reason. Stop and wait for "go".
```

**6.2 Implement** `[FLASH, Build]`
```
go. Implement the minimum to pass: webhook sending in a background task with a bounded timeout and bounded retries, delivery records persisted, pure metric functions with no I/O, and the dashboard cards using them. Never await a webhook inside the check loop. Run unit_06 tests, then the full suite. If the same test fails twice for the same cause, stop and show me, no third attempt. Don't touch files outside your list.
```

**6.3 Review** `[PRO, Plan]`
```
Review git diff main...HEAD against PLAN.md and DECISIONS.md and the fixtures. Max 8 by severity. Check specifically: a webhook awaited inside the check loop; unbounded retries; duplicate delivery after a restart or when two evaluations race; division by zero or 100% shown with no data; degraded checks counted the wrong way; a negative error budget displayed; metrics recomputed with heavy queries on every page load; timezone mixing in MTTD/MTTR; a figure shown without the estimate label. Then 3 lines per changed file. Don't edit code.
```
Then **CLOSE** `06`, **QUIZ**, commit, `bash scripts/unit-done.sh 06 notify-metrics`.
Viva questions to expect: how is a duplicate webhook prevented after a restart? Why count-based availability, and what does it get wrong? What does MTTD mean here and what can't it see?

---

## UNIT 7: Verification and handover (about 16 min, PRO)
Needs: nothing new. Branch: `bash scripts/unit-start.sh 07 verification`. Demo: one command runs the acceptance script and prints PASS.

**7.1 Coverage audit of my test plan** `[PRO, Plan]`
```
Read tests/, docs/TESTS.md and PLAN.md section 10. My required tests:
Unit: healthy, degraded and failed classification; consecutive failure and recovery thresholds; no duplicate active incidents for one service; availability, MTTD, MTTR and error-budget calculations.
Integration: a health check calls a mock /health and persists the result; a down service opens an incident and sends a webhook; a recovered service resolves the incident and sends a recovery webhook; a slow service does not block checks for other services.
For each, name the test file and test that implements it, or write MISSING. Also list any must-have #1-#10 with no test at all. Don't write tests.
```

**7.2 Fill the missing integration tests** `[FLASH, Build]`
```
Read the MISSING list from the last audit in this session and docs/TESTS.md. Write only the missing tests, marker unit_07, using in-process fake HTTP servers and an injected clock, no dependence on the real compose stack. Run them, then the full suite. If a test fails twice for the same cause, stop and show me. Don't change product code; if a test exposes a product bug, list it and stop.
```

**7.3 Full-drill acceptance test** `[PRO, Plan for the step list, then FLASH, Build for the script]`
```
Read docs/STARTER_KIT.md and DECISIONS.md. First list the expected observable result of each step: (1) start the complete app and the mock services; (2) all four services show healthy; (3) call payments /control/down; (4) after the failure threshold: payments DOWN, one open incident, a timeline entry, a webhook received by the receiver; (5) acknowledge the incident and add a note; (6) call payments /control/reset; (7) after the recovery threshold: payments healthy, incident resolved, a recovery event, a recovery webhook, and the public status page updated; (8) the metrics show MTTD and MTTR for the incident. Then write one acceptance script that polls with timeouts instead of fixed sleeps, reads short intervals from config so it finishes in under 90 seconds, always calls /control/reset in a finally block, and prints clear PASS/FAIL per step. No new product code.
```

**7.4 Hazard hunt over the whole product** `[PRO, Plan]`
```
Read src/ and tests/. List concrete failures with file and line, no fixes: (1) a slow or hung service delaying another's checks; (2) duplicate incidents or webhooks after a restart or overlapping checks; (3) a webhook receiver outage losing or looping notifications; (4) the public page leaking health URLs, owners or note text; (5) availability dividing by zero or showing 100% on no data; (6) timestamps in mixed time zones; (7) operator actions reachable without going through the operator routes. Mark each CONFIRMED or SUSPECTED with evidence.
```

**7.5 Fresh-clone and docs check** `[FLASH, Build]`
```
git clone . /tmp/fresh and follow README.md literally. List every command, assumption (ports, env vars, tools) and failure. Then compare README.md, docs/TESTS.md and PROGRESS.md with the code and the latest test results and list mismatches with file and line. Don't fix, and don't edit PLAN.md.
```

**7.6 Evidence for REVIEW.md** `[PRO, Plan]`
```
From LOG.md tags and git log, list every point where AI output was wrong, untested, over-scoped or rejected, and how I caught it. Then list what you think is weakest in the product. Evidence only; I'll write REVIEW.md and DECISIONS.md myself.
```

**7.7 Viva and live change** `[PRO, Plan]`
```
Act as two Acko engineers. Pick a random function in src/, ask me to explain it, wait, then say what I got wrong. Then pick one decision from DECISIONS.md and challenge it. After 3 rounds give me a 5-minute live change on Pulse (for example: make the degraded threshold per-service, add a field to the webhook payload, change the availability window). Wait for my result, then critique it.
```

**7.8 Ship checklist** `[shell, not AI]`
```
make secrets-check
```
Then: `opencode export` for every session into `transcripts/`, NotebookLM and other chats into `transcripts/prep/`, fill the "AI use (declared)" table in README.md, write REVIEW.md and finalise DECISIONS.md in your own words, push before the deadline.

Then **CLOSE** `07`, commit, `bash scripts/unit-done.sh 07 verification`.

---

## 5. Coverage check: every must-have has a unit
| # | Must-have | Unit prompts |
|---|---|---|
| 1 | Service catalogue (API + UI) | U1 (API), U4 (ADDED form) |
| 2 | Health checking | U2 |
| 3 | Service state | U3 |
| 4 | Incidents | U3 (engine), U4 (ack, notes, timeline) |
| 5 | Reliability tracking | U6 |
| 6 | Operator dashboard | U4 (+ ADDED recent response times) |
| 7 | Public status page | U5 (+ ADDED history) |
| 8 | Notifications | U6 |
| 9 | Product metrics | U2 (lag, duration), U6 |
| 10 | Runnable | U0, U7 |