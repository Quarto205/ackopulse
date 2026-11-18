"""Unit 2 — health-check engine tests.

Fake HTTP servers + injected clock; no compose stack; no sleep > 1 s.
"""
import asyncio
import socket
import threading
import time
from datetime import timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import aiosqlite
import pytest

from src.pulse.clock import clock
from src.pulse.config import settings


# ---------------------------------------------------------------- fake server
class FakeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/slow"):
            import re
            m = re.search(r"ms=(\d+)", self.path)
            ms = int(m.group(1)) if m else 300
            time.sleep(ms / 1000)
            self.send_response(200)
        elif self.path.startswith("/error500"):
            self.send_response(500)
        else:
            self.send_response(200)
        self.end_headers()

    def log_message(self, *a):  # silence
        pass


@pytest.fixture(scope="module")
def fake_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@pytest.fixture
def dead_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# ---------------------------------------------------------------- helpers
async def add_service(db, name, url, interval=10, next_check_at=None):
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}svc={name}"  # health_url is UNIQUE
    now = clock.now().isoformat()
    await db.execute(
        """INSERT INTO services (name, slug, health_url, owner, interval_seconds,
           slo_target, enabled, current_state, consecutive_failures,
           consecutive_successes, next_check_at, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 1, 'HEALTHY', 0, 0, ?, ?)""",
        (name, name, url, "t@t.io", interval, 99.9, next_check_at or now, now),
    )
    await db.commit()
    cur = await db.execute("SELECT id FROM services WHERE name = ?", (name,))
    return (await cur.fetchone())[0]


async def set_due(db, service_id, offset_seconds=-1):
    past = (clock.now() + timedelta(seconds=offset_seconds)).isoformat()
    await db.execute(
        "UPDATE services SET next_check_at = ? WHERE id = ?", (past, service_id)
    )
    await db.commit()


def make_scheduler():
    from src.pulse.checker.scheduler import Scheduler
    return Scheduler()


# ---------------------------------------------------------------- tests
@pytest.mark.unit_02
async def test_only_due_services_selected(initialized_db, fake_server):
    """Due, not due, and exactly-due services."""
    db_file = initialized_db
    async with aiosqlite.connect(db_file) as db:
        now = clock.now()
        due = await add_service(db, "due", fake_server)
        not_due = await add_service(
            db, "notdue", fake_server,
            next_check_at=(now + timedelta(seconds=60)).isoformat(),
        )
        exactly = await add_service(db, "exact", fake_server, next_check_at=now.isoformat())
        sched = make_scheduler()
        await sched.run_once(db)
        rows = await (await db.execute(
            "SELECT service_id FROM health_checks")).fetchall()
        ids = {r[0] for r in rows}
        assert due in ids and exactly in ids
        assert not_due not in ids


@pytest.mark.unit_02
async def test_slow_check_does_not_block_fast(initialized_db, fake_server):
    """4 services, one sleeps 400ms; fast results persist before slow finishes."""
    db_file = initialized_db
    async with aiosqlite.connect(db_file) as db:
        fast1 = await add_service(db, "f1", fake_server)
        fast2 = await add_service(db, "f2", fake_server)
        fast3 = await add_service(db, "f3", fake_server)
        slow = await add_service(db, "slow", fake_server + "/slow?ms=400")
        for sid in (fast1, fast2, fast3, slow):
            await set_due(db, sid)
        sched = make_scheduler()
        task = asyncio.create_task(sched.run_once(db))
        # poll: fast results should appear well before the slow one completes
        fast_persisted_at = None
        while not task.done():
            rows = await (await db.execute(
                "SELECT service_id FROM health_checks")).fetchall()
            if {fast1, fast2, fast3} <= {r[0] for r in rows}:
                fast_persisted_at = time.monotonic()
                break
            await asyncio.sleep(0.05)
        await task
        slow_row = await (await db.execute(
            "SELECT checked_at FROM health_checks WHERE service_id = ?", (slow,)
        )).fetchone()
        assert fast_persisted_at is not None  # fast persisted before slow finished
        assert slow_row is not None  # slow eventually persisted too


@pytest.mark.unit_02
async def test_timeout_persists_error_no_status(initialized_db, fake_server, monkeypatch):
    """Slower than timeout -> persisted row with error, null status."""
    monkeypatch.setattr(settings, "check_timeout_seconds", 0.15)
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "to", fake_server + "/slow?ms=600")
        await set_due(db, sid)
        sched = make_scheduler()
        await sched.run_once(db)
        row = await (await db.execute(
            "SELECT http_status, error_message, latency_ms, duration_ms "
            "FROM health_checks")).fetchone()
        assert row[0] is None
        assert row[1]  # error message present
        assert row[2] is not None and row[3] is not None


@pytest.mark.unit_02
async def test_500_persists_status_code(initialized_db, fake_server):
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "e5", fake_server + "/error500")
        await set_due(db, sid)
        await make_scheduler().run_once(db)
        row = await (await db.execute(
            "SELECT http_status FROM health_checks")).fetchone()
        assert row[0] == 500


@pytest.mark.unit_02
async def test_connection_refused_persists_error(initialized_db, dead_port):
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "ref", f"http://127.0.0.1:{dead_port}/health")
        await set_due(db, sid)
        await make_scheduler().run_once(db)
        row = await (await db.execute(
            "SELECT http_status, error_message FROM health_checks")).fetchone()
        assert row[0] is None and row[1]


@pytest.mark.unit_02
async def test_row_fields_complete(initialized_db, fake_server):
    """Every row has service_id, timestamp, status, latency, error, sched, started, duration."""
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "full", fake_server)
        await set_due(db, sid)
        await make_scheduler().run_once(db)
        cols = [r[1] for r in await (await db.execute(
            "PRAGMA table_info(health_checks)")).fetchall()]
        for col in ("service_id", "scheduled_at", "started_at", "checked_at",
                    "duration_ms", "http_status", "latency_ms", "state",
                    "error_message"):
            assert col in cols
        row = await (await db.execute(
            "SELECT service_id, scheduled_at, started_at, duration_ms FROM health_checks"
        )).fetchone()
        assert row[0] == sid
        assert row[1] <= row[2]  # scheduled <= started (lag >= 0)


@pytest.mark.unit_02
async def test_next_check_at_updated_no_catchup_burst(initialized_db, fake_server):
    """next_check_at = completion(now) + interval; long stall -> one run, not a burst."""
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "nc", fake_server, interval=10)
        # overdue by hours
        stale = (clock.now() - timedelta(hours=5)).isoformat()
        await db.execute(
            "UPDATE services SET next_check_at = ? WHERE id = ?", (stale, sid))
        await db.commit()
        before = clock.now().isoformat()
        await make_scheduler().run_once(db)
        # exactly one row for the service
        count = await (await db.execute(
            "SELECT COUNT(*) FROM health_checks WHERE service_id = ?", (sid,)
        )).fetchone()
        assert count[0] == 1
        nxt = await (await db.execute(
            "SELECT next_check_at FROM services WHERE id = ?", (sid,)
        )).fetchone()
        assert nxt[0] >= before  # anchored at completion + interval, not stale


@pytest.mark.unit_02
async def test_running_service_skipped_and_counted(initialized_db, fake_server, monkeypatch):
    """A service whose previous check is still running is skipped and counted."""
    monkeypatch.setattr(settings, "check_timeout_seconds", 0.8)
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "busy", fake_server + "/slow?ms=500")
        await set_due(db, sid)
        sched = make_scheduler()
        # simulate in-flight registration
        sched.in_flight.add(sid)
        assert sched.skipped_runs == 0
        await sched.run_once(db)
        assert sched.skipped_runs == 1
        rows = await (await db.execute(
            "SELECT COUNT(*) FROM health_checks")).fetchone()
        assert rows[0] == 0
        sched.in_flight.discard(sid)


@pytest.mark.unit_02
async def test_exception_in_one_check_does_not_stop_others(initialized_db, fake_server, monkeypatch):
    async with aiosqlite.connect(initialized_db) as db:
        ok = await add_service(db, "ok", fake_server)
        bad = await add_service(db, "bad", fake_server)
        await set_due(db, ok)
        await set_due(db, bad)
        sched = make_scheduler()
        orig = sched._probe_one
        async def boom(service):
            if service["name"] == "bad":
                raise RuntimeError("boom")
            return await orig(service)
        monkeypatch.setattr(sched, "_probe_one", boom)
        await sched.run_once(db)  # must not raise
        rows = await (await db.execute(
            "SELECT service_id FROM health_checks")).fetchall()
        assert ok in {r[0] for r in rows}
        assert bad not in {r[0] for r in rows}
