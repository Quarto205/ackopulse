"""Unit 5 — public status page tests (marker unit_05).

Privacy isolation (D-10), state collapse (D-21), 24h history (D-20),
title passthrough (D-22). Fake data via seeded temp DB, injected clock.
"""
from datetime import timedelta

import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

from src.pulse.clock import clock
from src.pulse.main import app


async def add_service(db, name, url="http://x/health", state="HEALTHY"):
    now = clock.now().isoformat()
    await db.execute(
        """INSERT INTO services (name, slug, health_url, owner, interval_seconds,
           slo_target, enabled, current_state, consecutive_failures,
           consecutive_successes, next_check_at, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 1, ?, 0, 0, ?, ?)""",
        (name, name, f"{url}/{name}", f"{name}@t.io", 10, 99.9, state, now, now),
    )
    await db.commit()
    cur = await db.execute("SELECT id FROM services WHERE name = ?", (name,))
    return (await cur.fetchone())[0]


async def open_incident(db, service_id, name, opened_at=None, status="active"):
    ts = opened_at or clock.now().isoformat()
    title = f"Service {name} is DOWN"
    await db.execute(
        "INSERT INTO incidents (service_id, opened_at, status, title) VALUES (?, ?, ?, ?)",
        (service_id, ts, status, title),
    )
    await db.commit()
    cur = await db.execute(
        "SELECT id FROM incidents WHERE title = ? AND opened_at = ?", (title, ts))
    return (await cur.fetchone())[0]


@pytest.fixture
async def client(initialized_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.unit_05
async def test_public_page_lists_services_with_collapsed_states(initialized_db, client):
    async with aiosqlite.connect(initialized_db) as db:
        await add_service(db, "svcA", state="HEALTHY")
        await add_service(db, "svcB", state="DEGRADED")
        await add_service(db, "svcC", state="DOWN")
    r = await client.get("/status")
    assert r.status_code == 200
    body = r.text
    assert "UP" in body and "ISSUE" in body and "OUTAGE" in body
    assert "svcA" in body and "svcB" in body and "svcC" in body


@pytest.mark.unit_05
async def test_public_page_never_leaks_private_fields(initialized_db, client):
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "leak", url="http://secret-host:9999/health")
        iid = await open_incident(db, sid, "leak")
        await db.execute(
            "INSERT INTO incident_events (incident_id, event_type, message, created_at)"
            " VALUES (?, 'note_added', 'operator secret note', ?)",
            (iid, clock.now().isoformat()),
        )
        await db.execute(
            "UPDATE incidents SET acknowledged_at = ?, acknowledged_by = 'op@x' WHERE id = ?",
            (clock.now().isoformat(), iid),
        )
        await db.commit()
    r = await client.get("/status")
    body = r.text
    for leak in ("secret-host", "9999", "leak@t.io", "operator secret note",
                 "acknowledged", "op@x", "health_url", "owner"):
        assert leak not in body, f"leaked: {leak}"


@pytest.mark.unit_05
async def test_public_page_shows_title_and_history_24h(initialized_db, client):
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "hist")
        now = clock.now()
        await open_incident(db, sid, "hist")  # active
        await open_incident(db, sid, "hist",  # resolved 2h ago -> included
                            opened_at=(now - timedelta(hours=2)).isoformat(),
                            status="resolved")
        await open_incident(db, sid, "hist",  # resolved 30h ago -> excluded (D-20)
                            opened_at=(now - timedelta(hours=30)).isoformat(),
                            status="resolved")
    r = await client.get("/status")
    assert "Service hist is DOWN" in r.text  # D-22 title passthrough
    assert r.text.count("Service hist is DOWN") == 2  # active + 2h; 30h excluded


@pytest.mark.unit_05
async def test_public_page_empty_state(initialized_db, client):
    r = await client.get("/status")
    assert r.status_code == 200
    assert "no incidents" in r.text.lower()


@pytest.mark.unit_05
async def test_public_page_is_read_only_and_separate_prefix(initialized_db, client):
    r = await client.post("/status", json={"x": 1})
    assert r.status_code == 405
    r2 = await client.get("/status")
    assert r2.status_code == 200


@pytest.mark.unit_05
async def test_public_page_escapes_html(initialized_db, client):
    async with aiosqlite.connect(initialized_db) as db:
        await add_service(db, "<script>alert(1)</script>")
    r = await client.get("/status")
    assert "<script>" not in r.text
    assert "&lt;script&gt;" in r.text
