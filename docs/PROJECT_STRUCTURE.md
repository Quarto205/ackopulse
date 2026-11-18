# PROJECT_STRUCTURE

Where every file lives and which unit creates it. Paths are proposals; keep them stable once Unit 0/1 land.

```
ackopulse/
├── README.md                  # startup, features, limitations, AI-use table (U7)
├── PLAN.md                    # product plan (frozen after Gate 1; AI never edits)
├── DECISIONS.md               # my decisions, own words (append only)
├── ARCHITECTURE.md            # design (this repo's source of truth for structure)
├── PROJECT_STRUCTURE.md       # this file
├── PROGRESS.md                # unit status, updated at CLOSE
├── LOG.md                     # AI errors/rejections/rollbacks
├── REVIEW.md                  # my own assessment (U7)
├── AGENTS.md                  # rules for AI agents
├── Dockerfile                 # U0
├── docker-compose.yml         # U0 (joins starter-kit network)
├── Makefile                   # U0: up, test, test U=nn, secrets-check
├── .env.example               # U0: config keys, no secrets
├── .gitignore                 # ignore .env, *.db, transcripts secrets
├── requirements.txt           # U0 (or pyproject.toml)
├── pytest.ini                 # U0: markers unit_00..unit_07
│
├── docs/
│   ├── STATEMENT.md           # original problem statement (paste)
│   ├── QUESTIONS.md           # product-owner questions and answers
│   ├── STARTER_KIT.md         # recon of supplied kit (pre-flight)
│   └── TESTS.md               # test cases, state table, metric fixtures
│
├── scripts/
│   ├── unit-start.sh          # new branch for a unit
│   ├── unit-done.sh           # merge/tag when a unit is done
│   ├── unit-rollback.sh       # abandon a unit
│   ├── secrets-check.sh       # used by make secrets-check
│   └── acceptance.py          # U7: full-drill acceptance script
│
├── src/pulse/
│   ├── __init__.py
│   ├── main.py                # U0: FastAPI app, lifespan (starts scheduler in U2)
│   ├── config.py              # U0: env-driven settings
│   ├── clock.py               # U1/U2: injectable clock (UTC)
│   ├── db.py                  # U1: aiosqlite connection, single write path, WAL
│   ├── schema.sql             # U1: tables and indexes
│   ├── seed.py                # U1: idempotent seed of the four services
│   ├── services.py            # U1: catalogue logic and validation
│   ├── checker/
│   │   ├── scheduler.py       # U2: due selection, loop, overlap skip
│   │   └── probe.py           # U2: httpx check, timeout, result capture
│   ├── state/
│   │   ├── classify.py        # U3: pure classification and transitions
│   │   └── incidents.py       # U3: persistence, one-active guard, events, ack, notes
│   ├── notify/
│   │   └── webhook.py         # U6: background sender, retries, delivery records
│   ├── metrics/
│   │   └── calc.py            # U6: pure availability, budget, MTTD, MTTR, checker perf
│   ├── api/
│   │   └── routes.py          # U1/U3/U6: /api/... JSON endpoints
│   └── web/
│       ├── operator.py        # U4: routes under /ops
│       ├── public.py          # U5: routes under /status (own data model)
│       ├── public_model.py    # U5: allowed fields only
│       └── templates/
│           ├── base.html
│           ├── operator/      # dashboard, incident detail, add service
│           └── public/        # status page
│
├── tests/
│   ├── conftest.py            # fake HTTP servers, injected clock, temp DB
│   ├── test_unit_00_smoke.py
│   ├── unit/                  # classification, thresholds, metrics, uniqueness
│   ├── integration/           # check persistence, webhook, slow isolation
│   └── acceptance/            # U7 full drill (separate from fast suite)
│
├── data/                      # SQLite file on a Docker volume (git-ignored)
└── transcripts/
    ├── (opencode exports per session)
    └── prep/                  # NotebookLM and other chat exports
```

## Route namespaces
| Prefix | Audience | Unit |
|---|---|---|
| `/health` | liveness | U0 |
| `/api/...` | JSON API | U1, U3, U6 |
| `/ops/...` | operator UI (no auth, local demo) | U4 |
| `/status` | public read-only page | U5 |

Operator and public routes must stay in separate prefixes (tested in U4/U5).

## Which unit creates what
| Unit | Creates |
|---|---|
| U0 | main.py, config.py, Dockerfile, compose, Makefile, .env.example, pytest.ini, smoke test |
| U1 | clock.py, db.py, schema.sql, seed.py, services.py, API routes for services |
| U2 | checker/scheduler.py, checker/probe.py, check result persistence |
| U3 | state/classify.py, state/incidents.py, ack/notes endpoints |
| U4 | web/operator.py, operator templates, registration form |
| U5 | web/public.py, web/public_model.py, public template |
| U6 | notify/webhook.py, metrics/calc.py, dashboard metric cards |
| U7 | acceptance script, gap-fill tests, README, REVIEW.md |
