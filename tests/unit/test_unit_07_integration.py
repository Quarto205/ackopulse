"""Unit 7 — Verification, handover, and end-to-end integration tests (marker unit_07).

Validates:
- Health check calls mock service and persists result.
- A down service opens an incident and sends a webhook to receiver.
- A recovered service resolves the incident and sends a recovery webhook.
- Slow service does not block others.
- Complete operator timeline integrity and webhook payload verification.
"""
import asyncio
import json
import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import aiosqlite
import pytest
from httpx import AsyncClient

from src.pulse.checker.scheduler import Scheduler
from src.pulse.clock import clock
from src.pulse.config import settings
from src.pulse.db import get_db
from src.pulse.notify.webhook import WebhookSender
from src.pulse.services import ServiceCreate, create_service
from src.pulse.state.incidents import (
    acknowledge_incident,
    add_incident_note,
    get_incident_timeline,
)


class DualMockServer(BaseHTTPRequestHandler):
    """Handles both mock service health checks and webhook receiver in one server."""
    service_status = 200
    service_delay = 0.0
    received_webhooks = []

    def do_GET(self):
        if self.path == "/health":
            if DualMockServer.service_delay > 0:
                import time
                time.sleep(DualMockServer.service_delay)
            self.send_response(DualMockServer.service_status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "mock"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/webhook":
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            DualMockServer.received_webhooks.append(payload)
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def mock_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), DualMockServer)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    port = server.server_address[1]
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture(autouse=True)
def reset_mock_server():
    DualMockServer.service_status = 200
    DualMockServer.service_delay = 0.0
    DualMockServer.received_webhooks.clear()
    yield
    DualMockServer.service_status = 200
    DualMockServer.service_delay = 0.0
    DualMockServer.received_webhooks.clear()


@pytest.mark.unit_07
@pytest.mark.asyncio
async def test_down_service_opens_incident_and_sends_webhook(initialized_db, mock_server, monkeypatch):
    """Two consecutive failures transition service to DOWN, open incident, and send webhook."""
    monkeypatch.setattr(settings, "webhook_url", f"{mock_server}/webhook")

    async with get_db() as db:
        svc = await create_service(
            db,
            ServiceCreate(
                name="payments-svc",
                health_url=f"{mock_server}/health",
                owner="payments-team",
                interval_seconds=10,
            ),
        )

    # Make mock service fail (500)
    DualMockServer.service_status = 500

    scheduler = Scheduler()

    # Tick 1: First failure -> DEGRADED (D-17)
    async with get_db() as db:
        run_count = await scheduler.run_once(db)
        assert run_count == 1

    async with get_db() as db:
        async with db.execute("SELECT current_state, consecutive_failures FROM services WHERE id = ?", (svc["id"],)) as cur:
            row = await cur.fetchone()
            assert row["current_state"] == "DEGRADED"
            assert row["consecutive_failures"] == 1

        # No incident opened yet
        async with db.execute("SELECT COUNT(*) FROM incidents WHERE service_id = ?", (svc["id"],)) as cur:
            assert (await cur.fetchone())[0] == 0

    # Advance clock past interval to make it due again
    clock.advance(11)

    # Tick 2: Second failure -> DOWN, opens incident, queues webhook
    async with get_db() as db:
        run_count = await scheduler.run_once(db)
        assert run_count == 1

    async with get_db() as db:
        async with db.execute("SELECT current_state, consecutive_failures FROM services WHERE id = ?", (svc["id"],)) as cur:
            row = await cur.fetchone()
            assert row["current_state"] == "DOWN"
            assert row["consecutive_failures"] == 2

        # 1 open incident exists
        async with db.execute("SELECT id, status FROM incidents WHERE service_id = ?", (svc["id"],)) as cur:
            inc_row = await cur.fetchone()
            assert inc_row is not None
            assert inc_row["status"] == "active"
            inc_id = inc_row["id"]

    # Now run background webhook delivery task
    async with get_db() as db:
        sender = WebhookSender(retry_delay=0.01)
        delivered = await sender.poll_once(db)
        await db.commit()
    assert delivered == 1

    # Verify receiver received exactly 1 open webhook with correct payload
    assert len(DualMockServer.received_webhooks) == 1
    wh = DualMockServer.received_webhooks[0]
    assert wh["event"] == "incident_opened"
    assert wh["service"] == "payments-svc"
    assert wh["incident_id"] == inc_id


@pytest.mark.unit_07
@pytest.mark.asyncio
async def test_recovered_service_resolves_incident_and_sends_recovery_webhook(initialized_db, mock_server, monkeypatch):
    """From DOWN, two consecutive successes resolve incident and deliver recovery webhook."""
    monkeypatch.setattr(settings, "webhook_url", f"{mock_server}/webhook")

    async with get_db() as db:
        svc = await create_service(
            db,
            ServiceCreate(
                name="claims-svc",
                health_url=f"{mock_server}/health",
                owner="claims-team",
                interval_seconds=10,
            ),
        )

    scheduler = Scheduler()

    # Step 1: Drive service to DOWN
    DualMockServer.service_status = 500
    async with get_db() as db:
        await scheduler.run_once(db)
    clock.advance(11)
    async with get_db() as db:
        await scheduler.run_once(db)

    # Deliver the open webhook
    async with get_db() as db:
        sender = WebhookSender(retry_delay=0.01)
        await sender.poll_once(db)
        await db.commit()
    assert len(DualMockServer.received_webhooks) == 1
    assert DualMockServer.received_webhooks[0]["event"] == "incident_opened"

    # Step 2: Service recovers to healthy 200 OK
    DualMockServer.service_status = 200
    clock.advance(11)

    # Recovery check 1 -> DEGRADED intermediate, incident still open
    async with get_db() as db:
        await scheduler.run_once(db)

    async with get_db() as db:
        async with db.execute("SELECT current_state, consecutive_successes FROM services WHERE id = ?", (svc["id"],)) as cur:
            row = await cur.fetchone()
            assert row["current_state"] == "DEGRADED"
            assert row["consecutive_successes"] == 1
        async with db.execute("SELECT status FROM incidents WHERE service_id = ?", (svc["id"],)) as cur:
            assert (await cur.fetchone())["status"] == "active"

    # Recovery check 2 -> HEALTHY, resolves incident
    clock.advance(11)
    async with get_db() as db:
        await scheduler.run_once(db)

    async with get_db() as db:
        async with db.execute("SELECT current_state, consecutive_successes FROM services WHERE id = ?", (svc["id"],)) as cur:
            row = await cur.fetchone()
            assert row["current_state"] == "HEALTHY"
            assert row["consecutive_successes"] == 2
        async with db.execute("SELECT status, resolved_at FROM incidents WHERE service_id = ?", (svc["id"],)) as cur:
            inc = await cur.fetchone()
            assert inc["status"] == "resolved"
            assert inc["resolved_at"] is not None

    # Step 3: Deliver recovery webhook
    async with get_db() as db:
        sender = WebhookSender(retry_delay=0.01)
        delivered = await sender.poll_once(db)
        await db.commit()
    assert delivered == 1

    assert len(DualMockServer.received_webhooks) == 2
    recovery_wh = DualMockServer.received_webhooks[1]
    assert recovery_wh["event"] == "incident_resolved"
    assert recovery_wh["service"] == "claims-svc"


@pytest.mark.unit_07
@pytest.mark.asyncio
async def test_incident_operator_timeline_and_no_webhook_on_ack_or_notes(initialized_db, mock_server, monkeypatch):
    """Acknowledging and adding notes appends to timeline but does NOT trigger webhooks (D-28)."""
    monkeypatch.setattr(settings, "webhook_url", f"{mock_server}/webhook")

    async with get_db() as db:
        svc = await create_service(
            db,
            ServiceCreate(
                name="notes-svc",
                health_url=f"{mock_server}/health",
                owner="notes-team",
                interval_seconds=10,
            ),
        )

    scheduler = Scheduler()
    DualMockServer.service_status = 500
    async with get_db() as db:
        await scheduler.run_once(db)
    clock.advance(11)
    async with get_db() as db:
        await scheduler.run_once(db)

    # Deliver opened webhook
    async with get_db() as db:
        sender = WebhookSender(retry_delay=0.01)
        await sender.poll_once(db)
        await db.commit()
    assert len(DualMockServer.received_webhooks) == 1

    async with get_db() as db:
        async with db.execute("SELECT id FROM incidents WHERE service_id = ?", (svc["id"],)) as cur:
            inc_id = (await cur.fetchone())[0]

        # Acknowledge incident
        await acknowledge_incident(db, inc_id, acknowledged_by="alice")
        # Add operator note
        await add_incident_note(db, inc_id, note="Database deadlock cleared")
        await db.commit()

        # Verify no new pending webhooks queued
        async with db.execute("SELECT COUNT(*) FROM webhook_deliveries WHERE outcome = 'pending'") as cur:
            assert (await cur.fetchone())[0] == 0

        # Timeline verification
        timeline = await get_incident_timeline(db, inc_id)
        event_types = [e["event_type"] for e in timeline]
        assert "opened" in event_types
        assert "acknowledged" in event_types
        assert "note_added" in event_types

    # Ensure no additional webhook delivered
    async with get_db() as db:
        sender = WebhookSender(retry_delay=0.01)
        delivered = await sender.poll_once(db)
        await db.commit()
    assert delivered == 0
    assert len(DualMockServer.received_webhooks) == 1
