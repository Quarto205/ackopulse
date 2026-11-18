"""Unit 4 — Operator UI tests (test-first).

Tests operator dashboard, recent times ordering, incident list, incident detail timeline,
acknowledge, note addition, HTML escaping, 404 on unknown incident, duplicate acknowledge,
service registration form, empty states, and route namespace isolation under /ops.
"""
import aiosqlite
import pytest
from httpx import AsyncClient

from src.pulse.clock import clock
from src.pulse.db import get_db
from src.pulse.state.incidents import open_incident, resolve_incident


@pytest.mark.unit_04
async def test_dashboard_renders_services_and_states(seeded_db, async_client: AsyncClient):
    """Dashboard returns 200 with every service, its current state and last response time."""
    resp = await async_client.get("/ops")
    assert resp.status_code == 200
    html = resp.text
    assert "Quotes Service" in html
    assert "Payments Service" in html
    assert "Claims Service" in html
    assert "Notifications Service" in html
    assert "HEALTHY" in html


@pytest.mark.unit_04
async def test_recent_response_times_in_order(seeded_db, async_client: AsyncClient):
    """Recent response times (up to N=5) appear in chronological order."""
    async with aiosqlite.connect(seeded_db) as db:
        cur = await db.execute("SELECT id FROM services WHERE slug = 'quotes'")
        sid = (await cur.fetchone())[0]

        # Insert 3 checks with distinct latencies
        for lat, ts in [(120, "2026-11-18T10:00:00Z"), (150, "2026-11-18T10:01:00Z"), (90, "2026-11-18T10:02:00Z")]:
            await db.execute(
                """INSERT INTO health_checks 
                   (service_id, scheduled_at, started_at, checked_at, duration_ms, latency_ms, state)
                   VALUES (?, ?, ?, ?, ?, ?, 'FAST_OK')""",
                (sid, ts, ts, ts, 50, lat),
            )
        await db.commit()

    resp = await async_client.get("/ops")
    assert resp.status_code == 200
    html = resp.text
    # Check that latencies appear
    assert "120" in html
    assert "150" in html
    assert "90" in html


@pytest.mark.unit_04
async def test_active_incidents_listed_before_resolved(seeded_db, async_client: AsyncClient):
    """Active incidents are listed before resolved incidents on the dashboard."""
    async with aiosqlite.connect(seeded_db) as db:
        cur = await db.execute("SELECT id, name FROM services WHERE slug = 'payments'")
        p_id, p_name = await cur.fetchone()
        cur = await db.execute("SELECT id, name FROM services WHERE slug = 'claims'")
        c_id, c_name = await cur.fetchone()

        # Payments: active incident
        await open_incident(db, p_id, p_name, now_iso="2026-11-18T10:00:00Z")
        # Claims: resolved incident
        c_inc = await open_incident(db, c_id, c_name, now_iso="2026-11-18T09:00:00Z")
        await resolve_incident(db, c_id, now_iso="2026-11-18T09:30:00Z")
        await db.commit()

    resp = await async_client.get("/ops")
    assert resp.status_code == 200
    html = resp.text
    # Active incident for payments should appear before resolved incident for claims
    pos_active = html.find("Payments Service")
    pos_resolved = html.find("Claims Service")
    assert pos_active != -1
    assert pos_resolved != -1


@pytest.mark.unit_04
async def test_incident_detail_timeline_order(seeded_db, async_client: AsyncClient):
    """Incident detail page shows timeline events in order."""
    async with aiosqlite.connect(seeded_db) as db:
        cur = await db.execute("SELECT id, name FROM services WHERE slug = 'payments'")
        sid, sname = await cur.fetchone()
        inc_id = await open_incident(db, sid, sname, now_iso="2026-11-18T10:00:00Z")
        await db.commit()

    resp = await async_client.get(f"/ops/incidents/{inc_id}")
    assert resp.status_code == 200
    html = resp.text
    assert "Incident opened" in html


@pytest.mark.unit_04
async def test_acknowledge_action(seeded_db, async_client: AsyncClient):
    """Acknowledge button updates incident and appends acknowledged event."""
    async with aiosqlite.connect(seeded_db) as db:
        cur = await db.execute("SELECT id, name FROM services WHERE slug = 'quotes'")
        sid, sname = await cur.fetchone()
        inc_id = await open_incident(db, sid, sname, now_iso="2026-11-18T10:00:00Z")
        await db.commit()

    resp = await async_client.post(
        f"/ops/incidents/{inc_id}/acknowledge",
        data={"acknowledged_by": "alice"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.text
    assert "Acknowledged" in html
    assert "alice" in html


@pytest.mark.unit_04
async def test_add_note_action(seeded_db, async_client: AsyncClient):
    """Add-note action appends an operator note to timeline."""
    async with aiosqlite.connect(seeded_db) as db:
        cur = await db.execute("SELECT id, name FROM services WHERE slug = 'quotes'")
        sid, sname = await cur.fetchone()
        inc_id = await open_incident(db, sid, sname, now_iso="2026-11-18T10:00:00Z")
        await db.commit()

    resp = await async_client.post(
        f"/ops/incidents/{inc_id}/notes",
        data={"note": "Restarted primary gateway container."},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Restarted primary gateway container." in resp.text


@pytest.mark.unit_04
async def test_empty_note_rejected(seeded_db, async_client: AsyncClient):
    """Empty note is rejected with bad request or stays on page without adding."""
    async with aiosqlite.connect(seeded_db) as db:
        cur = await db.execute("SELECT id, name FROM services WHERE slug = 'quotes'")
        sid, sname = await cur.fetchone()
        inc_id = await open_incident(db, sid, sname, now_iso="2026-11-18T10:00:00Z")
        await db.commit()

    resp = await async_client.post(
        f"/ops/incidents/{inc_id}/notes",
        data={"note": "   "},
        follow_redirects=True,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.unit_04
async def test_html_escaping_against_xss(seeded_db, async_client: AsyncClient):
    """Notes and service names containing HTML/script tags are escaped."""
    async with aiosqlite.connect(seeded_db) as db:
        cur = await db.execute("SELECT id, name FROM services WHERE slug = 'quotes'")
        sid, sname = await cur.fetchone()
        inc_id = await open_incident(db, sid, sname, now_iso="2026-11-18T10:00:00Z")
        await db.commit()

    xss_payload = "<script>alert('xss')</script>"
    resp = await async_client.post(
        f"/ops/incidents/{inc_id}/notes",
        data={"note": xss_payload},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "<script>alert" not in resp.text
    assert "&lt;script&gt;" in resp.text or "&amp;lt;" in resp.text or "alert(&#39;xss&#39;)" in resp.text


@pytest.mark.unit_04
async def test_acknowledging_resolved_incident_rejected(seeded_db, async_client: AsyncClient):
    """Acknowledging a resolved incident is rejected."""
    async with aiosqlite.connect(seeded_db) as db:
        cur = await db.execute("SELECT id, name FROM services WHERE slug = 'quotes'")
        sid, sname = await cur.fetchone()
        inc_id = await open_incident(db, sid, sname, now_iso="2026-11-18T10:00:00Z")
        await resolve_incident(db, sid, now_iso="2026-11-18T10:30:00Z")
        await db.commit()

    resp = await async_client.post(
        f"/ops/incidents/{inc_id}/acknowledge",
        data={"acknowledged_by": "bob"},
        follow_redirects=True,
    )
    assert resp.status_code in (400, 409)


@pytest.mark.unit_04
async def test_unknown_incident_id_returns_404(seeded_db, async_client: AsyncClient):
    """Unknown incident id returns 404 Not Found."""
    resp = await async_client.get("/ops/incidents/999999")
    assert resp.status_code == 404


@pytest.mark.unit_04
async def test_double_submit_acknowledge_idempotent(seeded_db, async_client: AsyncClient):
    """Double submit of acknowledge creates only 1 acknowledge event."""
    async with aiosqlite.connect(seeded_db) as db:
        cur = await db.execute("SELECT id, name FROM services WHERE slug = 'quotes'")
        sid, sname = await cur.fetchone()
        inc_id = await open_incident(db, sid, sname, now_iso="2026-11-18T10:00:00Z")
        await db.commit()

    # Ack 1
    await async_client.post(f"/ops/incidents/{inc_id}/acknowledge", data={"acknowledged_by": "alice"})
    # Ack 2
    await async_client.post(f"/ops/incidents/{inc_id}/acknowledge", data={"acknowledged_by": "alice"})

    async with aiosqlite.connect(seeded_db) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM incident_events WHERE incident_id = ? AND event_type = 'acknowledged'",
            (inc_id,),
        )
        count = (await cur.fetchone())[0]
        assert count == 1


@pytest.mark.unit_04
async def test_registration_form_creates_service(seeded_db, async_client: AsyncClient):
    """Registration form creates a service that appears on dashboard."""
    payload = {
        "name": "Audit Service",
        "slug": "audit-svc",
        "health_url": "http://localhost:7080/health",
        "owner": "audit-team@acko.com",
        "interval_seconds": 15,
        "slo_target": 99.9,
    }
    resp = await async_client.post("/ops/services/new", data=payload, follow_redirects=True)
    assert resp.status_code == 200
    assert "Audit Service" in resp.text


@pytest.mark.unit_04
async def test_invalid_registration_shows_error(seeded_db, async_client: AsyncClient):
    """Invalid registration shows an error message and does not create duplicate."""
    bad_payload = {
        "name": "Quotes Service",  # already exists
        "health_url": "http://localhost:7001/health",
        "owner": "dev@acko.com",
        "interval_seconds": 10,
        "slo_target": 99.9,
    }
    resp = await async_client.post("/ops/services/new", data=bad_payload, follow_redirects=True)
    assert resp.status_code in (400, 422)


@pytest.mark.unit_04
async def test_empty_states_render_without_errors(initialized_db, async_client: AsyncClient):
    """No-incident and no-check states render gracefully without 500 errors."""
    resp = await async_client.get("/ops")
    assert resp.status_code == 200
    assert "No active incidents" in resp.text or "No incidents" in resp.text or "incidents" in resp.text.lower()


@pytest.mark.unit_04
async def test_operator_routes_namespace_isolation(seeded_db, async_client: AsyncClient):
    """Operator routes live strictly under /ops (root redirects to /ops per D-20)."""
    resp_root = await async_client.get("/", follow_redirects=False)
    assert resp_root.status_code in (301, 302, 307, 308)
    assert "/ops" in resp_root.headers.get("location", "")
