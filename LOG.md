# LOG — AI events and errors

Record of AI errors, rejections, fixes, and rollbacks.

## Entries

- [2026-11-18 18:21 UTC] Unit 1 test fixture error: `Settings` dataclass had `frozen=True`, raising `dataclasses.FrozenInstanceError` when `monkeypatch.setattr(settings, "db_path", ...)` was run in `tests/conftest.py`. Fixed by removing `frozen=True` from `src/pulse/config.py`. All 9 Unit 1 tests passed immediately after.
- [2026-11-18 19:58 UTC] Unit 2: AI-WRONG — first scheduler draft had an internal `classify` placeholder colliding with a shadow import and a hardcoded `settings.db_path` in `_persist`; refactored to a clean `classify()` and immediate per-probe transaction (D-14). AI-WRONG — test fixture appended a path suffix to URLs, breaking `?ms=` query parsing; fixed with `?svc=` param. Design choice flagged: per-probe `httpx.AsyncClient` added ~0.5 s Windows overhead; switched to one shared client per scheduler per ARCHITECTURE.md §8. Result: 9/9 unit_02, 19/19 total.
- [2026-11-18 20:04 UTC] Unit 3: AI-WRONG — `get_incident_timeline` attempted `dict(row)` on raw tuples without `db.row_factory` set on the connection, raising `TypeError`. Fixed by unpacking tuple indices explicitly into dictionary items. `fake_server` test fixture centralized in `tests/conftest.py`. Result: 16/16 unit_03, 35/35 full suite.
