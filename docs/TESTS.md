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
| T2-1 | Only due services selected (due, not due, exactly due) | | NOT RUN |
| T2-2 | Slow service does not delay others; fast results persisted first | | NOT RUN |
| T2-3 | Timeout persists row with error and no status | | NOT RUN |
| T2-4 | 500 persists status code | | NOT RUN |
| T2-5 | Connection refused persists error | | NOT RUN |
| T2-6 | Row has all required fields incl. lag and duration | | NOT RUN |
| T2-7 | next_check_at updated; no catch-up burst after stall | | NOT RUN |
| T2-8 | Overlapping run skipped and counted | | NOT RUN |
| T2-9 | Restart with overdue checks runs each once | | NOT RUN |
| T2-10 | Exception in one check does not stop others | | NOT RUN |

### Unit 3 (unit_03)
| ID | Test | Criterion | Status |
|---|---|---|---|
| | One test per row of the state machine table below, plus: one-active-incident guard, event ordering, idempotent ack, restart reload | | NOT RUN |

### Unit 4 (unit_04)
| ID | Test | Criterion | Status |
|---|---|---|---|
| | Dashboard, recent times, ordering, timeline, ack, notes, escaping, 404, double submit, registration form, empty states, route prefix | | NOT RUN |

### Unit 5 (unit_05)
| ID | Test | Criterion | Status |
|---|---|---|---|
| | Public page content, no leaks (URL, owner, notes, ack), read-only, 405 on writes, empty states, escaping | | NOT RUN |

### Unit 6 (unit_06)
| ID | Test | Criterion | Status |
|---|---|---|---|
| | Webhook open/resolve once, delivery records, retries, restart safety, no duplicates, metrics equal fixtures, "n/a" on no data, estimate label | | NOT RUN |

### Unit 7 (unit_07)
| ID | Test | Criterion | Status |
|---|---|---|---|
| | Audit gaps filled; full-drill acceptance script | | NOT RUN |

## State machine table (Unit 3.0)
Filled from prompt 3.0 using only rules recorded in DECISIONS.md. Mark undetermined rows OPEN.

| Current state | Event | Next state | Counters after | Incident action | Event logged | Status |
|---|---|---|---|---|---|---|
| | | | | | | |

## Metric fixtures (Unit 6.0)
Hand-computed expected values with arithmetic. Include: no-data, window boundary (check exactly 24 h old), exhausted budget.

(paste fixtures here)

## Required test plan coverage (PLAN.md section 10)
| Required test | Implemented by | Status |
|---|---|---|
| Classification: healthy, degraded, failed | | PENDING (U3) |
| Consecutive failure and recovery thresholds | | PENDING (U3) |
| No duplicate active incidents | | PENDING (U3) |
| Availability, MTTD, MTTR, error-budget calculations | | PENDING (U6) |
| Integration: check persists result from mock /health | | PENDING (U2) |
| Integration: down service opens incident and sends webhook | | PENDING (U3, U6) |
| Integration: recovery resolves incident and sends recovery webhook | | PENDING (U3, U6) |
| Integration: slow service does not block others | | PENDING (U2) |
| Acceptance: full failure-to-recovery flow | | PENDING (U7) |
