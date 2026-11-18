# LOG — AI events and errors

Record of AI errors, rejections, fixes, and rollbacks.

## Entries

- [2026-11-18 18:21 UTC] Unit 1 test fixture error: `Settings` dataclass had `frozen=True`, raising `dataclasses.FrozenInstanceError` when `monkeypatch.setattr(settings, "db_path", ...)` was run in `tests/conftest.py`. Fixed by removing `frozen=True` from `src/pulse/config.py`. All 9 Unit 1 tests passed immediately after.
