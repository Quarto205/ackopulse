# TESTS

Updated at each CLOSE. One row per test case. Marker = pytest marker.

## How to run
- `make test U=<nn>` runs `pytest -m unit_<nn>`
- `make test` runs everything
- Acceptance script: (fill in at Unit 7)

## Last run
| Date/time (UTC) | Scope | Passed | Failed | Notes |
|---|---|---|---|---|
| 2026-11-18 12:51:25 | unit_00, unit_01 | 10 | 0 | All tests passed |
| 2026-11-18 19:55:00 | unit_00..unit_02 | 19 | 0 | 9 unit_02 tests pass; full suite 19/19 |
| 2026-11-18 20:15:00 | unit_00..unit_05 | 56 | 0 | 6 unit_05 tests pass; full suite 56/56 |
| 2026-11-18 20:50:00 | unit_00..unit_06 | 66 | 0 | 10 unit_06 tests pass; full suite 66/66 |
| 2026-11-18 19:58:30 | unit_00..unit_03 | 31 | 0 | 12 unit_03 classifier tests pass; full suite 31/31 |
| 2026-11-18 20:05:00 | unit_00..unit_03 | 35 | 0 | 16 unit_03 tests pass; full suite 35/35 |
| 2026-11-18 20:11:30 | unit_00..unit_04 | 50 | 0 | 15 unit_04 tests pass; full suite 50/50 |

## Test cases by unit

### Unit 0 (marker unit_00)
| ID | Test | Criterion | Status |
|---|---|---|---|
| T0-1 | Smoke: /health returns ok | App runs | PASSED |

### Unit 1 (unit_01)
| ID | Test | Criterion | Status |
|---|---|---|---|
| T1-1 | App starts, /health ok | Returns 200 {"status": "ok"} | PASSED |
| T1-2 | Tables created on empty DB | Schema creates all 5 tables | PASSED |
| T1-3 | Restart keeps data | Reconnection keeps persisted rows | PASSED |
| T1-4 | Seed inserts exactly 4; twice still 4 | Idempotent seed function | PASSED |
| T1-5 | Seeded health URLs match STARTER_KIT.md | Correct ports 7001-7004 | PASSED |
| T1-6 | List returns all | GET /api/services returns 4 seeded services | PASSED |
| T1-7 | Valid registration appears in list | POST /api/services creates and lists | PASSED |
| T1-8 | Invalid URL, missing field, bounds, duplicate name/URL rejected with 4xx | Validation and duplicate checks | PASSED |
| T1-9 | Schema has counter, state, next_check_at, first-failure columns | All required columns present | PASSED |

### Unit 2 (unit_02)
| ID | Test | Criterion | Status |
|---|---|---|---|
| T2-1 | Only due services selected (due, not due, exactly due) | Runnable set excludes not-due; includes due + exactly-due | PASSED |
| T2-2 | Slow service does not delay others; fast results persisted first | Fast rows appear while slow check in flight (poll, no fixed sleep) | PASSED |
| T2-3 | Timeout persists row with error and no status | http_status NULL, error set, latency/duration captured | PASSED |
| T2-4 | 500 persists status code | http_status = 500 | PASSED |
| T2-5 | Connection refused persists error | status NULL, error message set | PASSED |
| T2-6 | Row has all required fields incl. lag and duration | Columns present; scheduled_at <= started_at | PASSED |
| T2-7 | next_check_at updated; no catch-up burst after stall | Overdue 5h -> exactly 1 check; next anchored now+interval | PASSED |
| T2-8 | Overlapping run skipped and counted | In-flight id skipped; skipped_runs == 1 | PASSED |
| T2-9 | Restart with overdue checks runs each once | Covered by T2-7 (overdue -> one row) | PASSED |
| T2-10 | Exception in one check does not stop others | gather(return_exceptions=True); other service persists | PASSED |

### Unit 3 (unit_03)
| ID | Test | Criterion | Status |
|---|---|---|---|
| T3-1 | Fast successful response | HEALTHY + FAST_OK -> HEALTHY, succ+1 | PASSED |
| T3-2 | Slow successful response | HEALTHY + SLOW_OK -> DEGRADED (D-16) | PASSED |
| T3-3 | First consecutive failed check | HEALTHY + FAILED -> DEGRADED, fail=1 (D-17) | PASSED |
| T3-4 | Failure threshold reached | fail >= 2 -> DOWN, action="open" | PASSED |
| T3-5 | Recovery threshold not yet reached | DOWN + 1 FAST_OK -> DEGRADED intermediate | PASSED |
| T3-6 | Recovery threshold reached | 2 FAST_OK -> HEALTHY, action="resolve" | PASSED |
| T3-7 | Counter resets on outcome change | Failure resets succ; SLOW_OK resets fail | PASSED |
| T3-8 | All permitted state transitions | HEALTHY, DEGRADED, DOWN transitions | PASSED |
| T3-9 | Boundary conditions at exact thresholds | 1499ms vs 1500ms; fail=2; succ=2 | PASSED |
| T3-10 | Skipped checks do not alter counters | SKIP leaves state and counters untouched | PASSED |
| T3-11 | Initial service state defaults | None -> HEALTHY, 0/0 | PASSED |
| T3-12 | Repeated classifications deterministic | Pure function idempotency | PASSED |
| T3-13 | DB first failure marks DEGRADED | Integration test in DB | PASSED |
| T3-14 | DB 2 failures opens single incident | Integration test in DB | PASSED |
| T3-15 | DB recovery resolves active incident | Integration test in DB | PASSED |
| T3-16 | Acknowledge and notes timeline | Timeline ordering, idempotency | PASSED |

### Unit 4 (unit_04)
| ID | Test | Criterion | Status |
|---|---|---|---|
| T4-1 | Dashboard renders services and states | /ops returns 200 with service table and states | PASSED |
| T4-2 | Recent response times in chronological order | Displays up to N=5 recent check latencies | PASSED |
| T4-3 | Active incidents listed before resolved | Order by status and opened time | PASSED |
| T4-4 | Incident detail timeline order | Chronological events displayed | PASSED |
| T4-5 | Acknowledge action updates incident | Sets acknowledged flag, by whom, and timeline event | PASSED |
| T4-6 | Add note appends to timeline | Note stored as timeline event | PASSED |
| T4-7 | Empty note rejected | Returns 400 Bad Request | PASSED |
| T4-8 | HTML escaping against XSS | Script tags rendered as escaped text | PASSED |
| T4-9 | Acknowledging resolved incident rejected | Returns 400 Bad Request | PASSED |
| T4-10 | Unknown incident id returns 404 | 404 Not Found | PASSED |
| T4-11 | Double submit acknowledge idempotent | Only 1 acknowledged event created | PASSED |
| T4-12 | Registration form creates service | Form submission creates service appearing on dashboard | PASSED |
| T4-13 | Invalid registration shows error | Returns 400 and preserves page error state | PASSED |
| T4-14 | Empty states render without errors | Graceful rendering when no incidents exist | PASSED |
| T4-15 | Operator routes namespace isolation | /ops isolation, / redirects to /ops per D-20 | PASSED |

### Unit 5 (unit_05)
| ID | Test | Criterion | Status |
|---|---|---|---|
| T5-1 | Public page lists services with collapsed states | UP/ISSUE/OUTAGE shown (D-21) | PASSED |
| T5-2 | No private fields leak | health_url, owner, notes, ack absent from HTML (D-10) | PASSED |
| T5-3 | Title passthrough + 24h history | Title shown; resolved >24h excluded (D-20, D-22) | PASSED |
| T5-4 | Empty state renders | 200 with "no incidents" message | PASSED |
| T5-5 | Read-only + separate prefix | POST /status -> 405; GET -> 200 | PASSED |
| T5-6 | HTML escaping | Service name `<script>` renders as text | PASSED |

### Unit 6 (unit_06)
| ID | Test | Criterion | Status |
|---|---|---|---|
| T6-1 | Pending delivery row on open | outcome=pending, key `{id}:incident_opened` (D-24) | PASSED |
| T6-2 | Sender POSTs and marks delivered | Payload event/service correct (D-06) | PASSED |
| T6-3 | Retries then records failure | attempt=3, outcome=failed (D-23) | PASSED |
| T6-4 | No duplicate delivery | delivered row never re-sent (D-24) | PASSED |
| T6-5 | Availability healthy-only | 2/4 in-window = 50%; 30h-old excluded (D-25) | PASSED |
| T6-6 | Availability no-data n/a | None, never 100% | PASSED |
| T6-7 | MTTD/MTTR formulas | mean(opened−first_failure)=1.5h; mean(resolved−opened)=1.5h (D-26) | PASSED |
| T6-8 | MTTD no-data n/a | (None, None) | PASSED |
| T6-9 | Error budget floored | 99.5/99.9→0; 99.95/99.9→0.05; 99.9/99.9→0 (D-27) | PASSED |
| T6-10 | /api/metrics/summary | 200; availability + estimate label present | PASSED |

### Unit 7 (unit_07)
| ID | Test | Criterion | Status |
|---|---|---|---|
| | Audit gaps filled; full-drill acceptance script | | NOT RUN |

## State machine table (Unit 3.0)
Filled from prompt 3.0 using rules recorded in DECISIONS.md (D-01, D-02, D-03, D-11, D-16, D-17).

| Current state | Event | Next state | Counters after | Incident action | Event logged | Status |
|---|---|---|---|---|---|---|
| HEALTHY | FAST_OK | HEALTHY | fail=0, succ=+1 | None | — | TESTED (T3-1) |
| HEALTHY | SLOW_OK | DEGRADED | fail=0, succ=0 | None | — | TESTED (T3-2) |
| HEALTHY | FAILED | DEGRADED | fail=1, succ=0 | None | — | TESTED (T3-3) |
| DEGRADED | FAILED (fail>=2) | DOWN | fail=+1, succ=0 | open | incident opened | TESTED (T3-4) |
| DEGRADED | FAILED (fail<2) | DEGRADED | fail=+1, succ=0 | None | — | TESTED (T3-8) |
| DEGRADED | FAST_OK (succ<2) | DEGRADED | fail=0, succ=+1 | None | — | TESTED (T3-5) |
| DEGRADED | FAST_OK (succ>=2) | HEALTHY | fail=0, succ=+1 | resolve | incident resolved | TESTED (T3-6) |
| DEGRADED | SLOW_OK | DEGRADED | fail=0, succ=0 | None | — | TESTED (T3-7) |
| DOWN | FAILED | DOWN | fail=+1, succ=0 | None | — | TESTED (T3-8) |
| DOWN | SLOW_OK | DOWN | fail=0, succ=0 | None | — | TESTED (T3-7) |
| DOWN | FAST_OK (succ<2) | DEGRADED | fail=0, succ=1 | None | — | TESTED (T3-5) |
| ANY | SKIP | ANY | unchanged | None | — | TESTED (T3-10) |

## Required test plan coverage (PLAN.md section 10)
| Required test | Implemented by | Status |
|---|---|---|
| Classification: healthy, degraded, failed | T3-1, T3-2, T3-3, T3-9 | DONE |
| Consecutive failure and recovery thresholds | T3-4, T3-5, T3-6 | DONE |
| No duplicate active incidents | T3-14, schema partial index | DONE |
| Availability, MTTD, MTTR, error-budget calculations | T6-5..T6-9 | DONE |
| Unit tests: classification, thresholds (state machine) | U3 suite | DONE |
| Integration: check persists result from mock /health | T2-4/T2-6 (fake HTTP server) | DONE |
| Integration: down service opens incident and sends webhook | T3-14 (incident opened); webhook in U6 | DONE (Incident) / PENDING (Webhook) |
| Integration: recovery resolves incident and sends recovery webhook | T3-15 (incident resolved); webhook in U6 | DONE (Incident) / PENDING (Webhook) |
| Integration: slow service does not block others | T2-2 | DONE |
| Acceptance: full failure-to-recovery flow | | PENDING (U7) |
