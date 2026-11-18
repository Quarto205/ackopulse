"""Unit 6 — webhook notifications and reliability metrics (marker unit_06).

D-23 3 attempts / 2 s fixed delay (injectable), D-24 idempotency key,
D-25 healthy-only availability, D-26 MTTD/MTTR defs, D-27 floored budget,
D-28 background sender polling pending rows.
"""
import asyncio
import json
import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import aiosqlite
import pytest
from httpx import AsyncClient

from src.pulse.clock import clock


# ------------------------------------------------------------ fake receiver
class Receiver(BaseHTTPRequestHandler):
    store = []
    fail_next = 0

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if Receiver.fail_next > 0:
            Receiver.fail_next -= 1
            self.send_response(500)
        else:
            Receiver.store.append(payload)
            self.send_response(200)
        self.end_headers()

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def receiver():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    Receiver.store.clear()
    yield f"http://127.0.0.1:{server.server_address[1]}/"
    server.shutdown()


@pytest.fixture(autouse=True)
def reset_receiver():
    Receiver.store.clear()
    Receiver.fail_next = 0
    yield
    Receiver.store.clear()
    Receiver.fail_next = 0


# ------------------------------------------------------------ data helpers
async def add_service(db, name, state="HEALTHY", first_failure_at=None):
    now = clock.now().isoformat()
    await db.execute(
        """INSERT INTO services (name, slug, health_url, owner, interval_seconds,
           slo_target, enabled, current_state, consecutive_failures,
           consecutive_successes, first_failure_at, next_check_at, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 1, ?, 0, 0, ?, ?, ?)""",
        (name, name, f"http://x/{name}", f"{name}@t.io", 10, 99.9, state,
         first_failure_at, now, now),
    )
    await db.commit()
    cur = await db.execute("SELECT id FROM services WHERE name = ?", (name,))
    return (await cur.fetchone())[0]


async def add_check(db, service_id, state, checked_at=None, latency_ms=100):
    ts = (checked_at or clock.now()).isoformat()
    await db.execute(
        """INSERT INTO health_checks (service_id, scheduled_at, started_at,
           checked_at, duration_ms, http_status, latency_ms, state, error_message)
           VALUES (?, ?, ?, ?, ?, 200, ?, ?, NULL)""",
        (service_id, ts, ts, ts, latency_ms, latency_ms, state),
    )
    await db.commit()


async def add_incident(db, service_id, name, opened_at, resolved_at=None,
                       first_failure_at=None):
    title = f"Service {name} is DOWN"
    await db.execute(
        "INSERT INTO incidents (service_id, opened_at, resolved_at, status, title)"
        " VALUES (?, ?, ?, ?, ?)",
        (service_id, opened_at, resolved_at,
         "resolved" if resolved_at else "active", title),
    )
    await db.commit()


def pending_row(db_file):
    async def _go():
        async with aiosqlite.connect(db_file) as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM webhook_deliveries WHERE outcome = 'pending'")
            return (await cur.fetchone())[0]
    return _go


# ------------------------------------------------------------ webhook tests
@pytest.mark.unit_06
async def test_pending_delivery_row_created_on_open(initialized_db, receiver):
    from src.pulse.state.incidents import open_incident
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "p1", state="DOWN")
        iid = await open_incident(db, sid, "p1")
        assert iid
        cur = await db.execute(
            "SELECT COUNT(*) FROM webhook_deliveries WHERE outcome = 'pending'")
        assert (await cur.fetchone())[0] == 1
        cur = await db.execute(
            "SELECT idempotency_key FROM webhook_deliveries")
        key = (await cur.fetchone())[0]
        assert key == f"{iid}:incident_opened"


@pytest.mark.unit_06
async def test_sender_posts_and_marks_delivered(initialized_db, receiver, monkeypatch):
    from src.pulse.notify.webhook import WebhookSender
    from src.pulse.config import settings
    monkeypatch.setattr(settings, "webhook_url", receiver)
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "s1", state="DOWN")
        cur = await db.execute(
            """INSERT INTO webhook_deliveries (incident_id, event_type, attempt,
               outcome, idempotency_key, created_at) VALUES (?, 'incident_opened',
               0, 'pending', '5:incident_opened', ?)""",
            (sid, clock.now().isoformat()))
        await db.commit()
        await db.execute(
            "INSERT INTO incidents (id, service_id, opened_at, status, title)"
            " VALUES (1, ?, ?, 'active', 'Service s1 is DOWN')",
            (sid, clock.now().isoformat()))
        await db.commit()
        sender = WebhookSender(retry_delay=0.05, max_attempts=3)
        await sender.poll_once(db)
        cur = await db.execute("SELECT outcome FROM webhook_deliveries")
        assert (await cur.fetchone())[0] == "delivered"
        assert len(Receiver.store) == 1
        payload = Receiver.store[0]
        assert payload["event"] == "incident_opened"
        assert payload["service"] == "s1"


@pytest.mark.unit_06
async def test_sender_retries_then_records_failure(initialized_db, receiver):
    from src.pulse.notify.webhook import WebhookSender
    from src.pulse.config import settings
    import src.pulse.notify.webhook as wh
    import src.pulse.config as cfg
    # point module-level url at receiver
    wh.settings.webhook_url = receiver
    Receiver.fail_next = 5  # all attempts fail
    async with aiosqlite.connect(initialized_db) as db:
        await db.execute(
            """INSERT INTO webhook_deliveries (incident_id, event_type, attempt,
               outcome, idempotency_key, created_at) VALUES (1, 'incident_opened',
               0, 'pending', '9:incident_opened', ?)""",
            (clock.now().isoformat(),))
        await db.execute(
            "INSERT INTO incidents (id, service_id, opened_at, status, title)"
            " VALUES (1, 1, ?, 'active', 'Service x is DOWN')",
            (clock.now().isoformat(),))
        await db.execute(
            "INSERT INTO services (id, name, slug, health_url, owner, interval_seconds,"
            " slo_target, enabled, current_state, consecutive_failures,"
            " consecutive_successes, next_check_at, created_at)"
            " VALUES (1, 'x', 'x', 'http://x/health', 'x@t.io', 10, 99.9, 1,"
            " 'DOWN', 0, 0, ?, ?)",
            (clock.now().isoformat(), clock.now().isoformat()))
        await db.commit()
        sender = WebhookSender(retry_delay=0.05, max_attempts=3)
        await sender.poll_once(db)
        cur = await db.execute("SELECT outcome, attempt FROM webhook_deliveries")
        row = await cur.fetchone()
        assert row[0] == "failed"
        assert row[1] == 3  # 3 attempts recorded (D-23)
        assert len(Receiver.store) == 0


@pytest.mark.unit_06
async def test_no_duplicate_delivery_for_same_event(initialized_db, receiver):
    from src.pulse.notify.webhook import WebhookSender
    import src.pulse.notify.webhook as wh
    wh.settings.webhook_url = receiver
    async with aiosqlite.connect(initialized_db) as db:
        await db.execute(
            """INSERT INTO webhook_deliveries (incident_id, event_type, attempt,
               outcome, idempotency_key, created_at) VALUES (1, 'incident_opened',
               0, 'delivered', '1:incident_opened', ?)""",
            (clock.now().isoformat(),))
        await db.commit()
        sender = WebhookSender(retry_delay=0.05)
        await sender.poll_once(db)
        assert len(Receiver.store) == 0  # delivered row not re-sent (D-24)


# ------------------------------------------------------------ metric tests
@pytest.mark.unit_06
async def test_availability_healthy_only(initialized_db):
    from src.pulse.metrics.calc import availability
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "av")
        now = clock.now()
        await add_check(db, sid, "HEALTHY", checked_at=now - timedelta(hours=1))
        await add_check(db, sid, "HEALTHY", checked_at=now - timedelta(hours=2))
        await add_check(db, sid, "DEGRADED", checked_at=now - timedelta(hours=3))
        await add_check(db, sid, "FAILED", checked_at=now - timedelta(hours=4))
        # 30h-old healthy check is outside window
        await add_check(db, sid, "HEALTHY", checked_at=now - timedelta(hours=30))
        val = await availability(db, sid)
        assert val == 50.0  # 2 healthy of 4 in-window (D-25)


@pytest.mark.unit_06
async def test_availability_no_data_is_na(initialized_db):
    from src.pulse.metrics.calc import availability
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "empty")
        val = await availability(db, sid)
        assert val is None  # renders as "n/a", never 100%


@pytest.mark.unit_06
async def test_mttd_mttr_formulas(initialized_db):
    from src.pulse.metrics.calc import mttd_mttr
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "m", state="HEALTHY")
        now = clock.now()
        ff = now - timedelta(hours=4)
        await db.execute(
            "UPDATE services SET first_failure_at = ? WHERE id = ?", (ff.isoformat(), sid))
        await db.commit()
        # incident 1: opened 1h after first failure, resolved 2h later
        await add_incident(db, sid, "m", opened_at=(ff + timedelta(hours=1)).isoformat(),
                           resolved_at=(ff + timedelta(hours=3)).isoformat())
        # incident 2: opened 2h after ff, resolved 1h later
        await add_incident(db, sid, "m", opened_at=(ff + timedelta(hours=2)).isoformat(),
                           resolved_at=(ff + timedelta(hours=3)).isoformat())
        mttd, mttr = await mttd_mttr(db, sid)
        assert mttd == 1.5 * 3600  # mean(1h, 2h) seconds
        assert mttr == 1.5 * 3600  # mean(2h, 1h)


@pytest.mark.unit_06
async def test_mttd_no_data_na(initialized_db):
    from src.pulse.metrics.calc import mttd_mttr
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "nm")
        mttd, mttr = await mttd_mttr(db, sid)
        assert mttd is None and mttr is None


@pytest.mark.unit_06
async def test_error_budget_floored(initialized_db):
    from src.pulse.metrics.calc import error_budget_remaining
    # availability 99.5, SLO 99.9 -> budget 0.1 - 0.5 = -0.4 -> floored 0 (D-27)
    assert error_budget_remaining(99.5, 99.9) == 0.0
    # availability 99.95, SLO 99.9 -> 0.1 - 0.05 = 0.05
    assert abs(error_budget_remaining(99.95, 99.9) - 0.05) < 1e-9
    # exhausted: availability 99.9 -> 0.0
    assert error_budget_remaining(99.9, 99.9) == 0.0


@pytest.mark.unit_06
async def test_metrics_summary_endpoint(initialized_db, receiver):
    from httpx import ASGITransport
    from src.pulse.main import app
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "api")
        await add_check(db, sid, "HEALTHY")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/metrics/summary")
        assert r.status_code == 200
        data = r.json()
        assert "services" in data
        svc = [s for s in data["services"] if s["name"] == "api"][0]
        assert svc["availability"] == 100.0
        assert svc["estimate_label"] == "estimate from periodic checks"
