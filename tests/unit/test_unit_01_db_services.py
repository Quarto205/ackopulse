import aiosqlite
import pytest
from httpx import AsyncClient
from src.pulse.db import get_db, init_db
from src.pulse.seed import seed_services
from src.pulse.services import create_service, list_services, ServiceCreate


@pytest.mark.unit_01
async def test_t1_1_app_starts_health_ok(async_client: AsyncClient):
    """T1-1: App starts, /health returns ok."""
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.unit_01
async def test_t1_2_tables_created_on_empty_db(initialized_db):
    """T1-2: Tables created on empty DB."""
    async with aiosqlite.connect(str(initialized_db)) as db:
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
            tables = [row[0] for row in await cursor.fetchall()]
    assert "services" in tables
    assert "health_checks" in tables
    assert "incidents" in tables
    assert "incident_events" in tables
    assert "webhook_deliveries" in tables


@pytest.mark.unit_01
async def test_t1_3_restart_keeps_data(initialized_db):
    """T1-3: Reconnecting to existing DB retains persisted rows."""
    async with aiosqlite.connect(str(initialized_db)) as db:
        await db.execute(
            """
            INSERT INTO services (name, slug, health_url, owner, created_at)
            VALUES ('Persist Svc', 'persist-svc', 'http://localhost:9001/health', 'dev@acko.com', '2026-11-18T00:00:00Z')
            """
        )
        await db.commit()

    # Reconnect and verify data exists
    async with aiosqlite.connect(str(initialized_db)) as db:
        async with db.execute("SELECT name FROM services WHERE slug='persist-svc'") as cursor:
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "Persist Svc"


@pytest.mark.unit_01
async def test_t1_4_seed_inserts_exactly_4_and_idempotent(initialized_db):
    """T1-4: Seed inserts exactly 4; twice still 4."""
    await seed_services()
    async with aiosqlite.connect(str(initialized_db)) as db:
        async with db.execute("SELECT COUNT(*) FROM services") as cursor:
            count = (await cursor.fetchone())[0]
            assert count == 4

    # Run seed second time
    await seed_services()
    async with aiosqlite.connect(str(initialized_db)) as db:
        async with db.execute("SELECT COUNT(*) FROM services") as cursor:
            count = (await cursor.fetchone())[0]
            assert count == 4


@pytest.mark.unit_01
async def test_t1_5_seeded_health_urls_match_starter_kit(initialized_db):
    """T1-5: Seeded health URLs match STARTER_KIT.md services and ports."""
    await seed_services()
    async with aiosqlite.connect(str(initialized_db)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT slug, health_url FROM services") as cursor:
            rows = {row["slug"]: row["health_url"] for row in await cursor.fetchall()}

    assert "quotes" in rows and "7001" in rows["quotes"]
    assert "payments" in rows and "7002" in rows["payments"]
    assert "claims" in rows and "7003" in rows["claims"]
    assert "notifications" in rows and "7004" in rows["notifications"]


@pytest.mark.unit_01
async def test_t1_6_list_returns_all(seeded_db, async_client: AsyncClient):
    """T1-6: GET /api/services returns all registered services."""
    resp = await async_client.get("/api/services")
    assert resp.status_code == 200
    services = resp.json()
    assert len(services) == 4
    slugs = [s["slug"] for s in services]
    assert "quotes" in slugs
    assert "payments" in slugs
    assert "claims" in slugs
    assert "notifications" in slugs


@pytest.mark.unit_01
async def test_t1_7_valid_registration_appears_in_list(seeded_db, async_client: AsyncClient):
    """T1-7: POST /api/services registers service and appears in GET /api/services."""
    payload = {
        "name": "Auth Service",
        "slug": "auth-service",
        "health_url": "http://localhost:7005/health",
        "owner": "auth-team@acko.com",
        "interval_seconds": 15,
        "slo_target": 99.95,
    }
    resp = await async_client.post("/api/services", json=payload)
    assert resp.status_code == 201
    created = resp.json()
    assert created["name"] == "Auth Service"
    assert created["current_state"] == "HEALTHY"

    # Verify present in list
    list_resp = await async_client.get("/api/services")
    names = [s["name"] for s in list_resp.json()]
    assert "Auth Service" in names


@pytest.mark.unit_01
async def test_t1_8_invalid_registration_rejected(seeded_db, async_client: AsyncClient):
    """T1-8: Invalid URL, missing fields, out of bounds, duplicate rejected with 4xx."""
    # 1. Invalid URL scheme
    bad_url = {
        "name": "Bad URL Service",
        "health_url": "ftp://localhost:7000/health",
        "owner": "dev@acko.com",
    }
    r1 = await async_client.post("/api/services", json=bad_url)
    assert r1.status_code in (400, 422)

    # 2. Missing required field (name)
    missing_name = {
        "health_url": "http://localhost:7006/health",
        "owner": "dev@acko.com",
    }
    r2 = await async_client.post("/api/services", json=missing_name)
    assert r2.status_code == 422

    # 3. Interval out of bounds (< 1)
    bad_interval = {
        "name": "Bad Interval",
        "health_url": "http://localhost:7007/health",
        "owner": "dev@acko.com",
        "interval_seconds": 0,
    }
    r3 = await async_client.post("/api/services", json=bad_interval)
    assert r3.status_code == 422

    # 4. Duplicate name/health_url
    duplicate = {
        "name": "Quotes Service",  # already exists from seed
        "health_url": "http://localhost:7999/health",
        "owner": "dev@acko.com",
    }
    r4 = await async_client.post("/api/services", json=duplicate)
    assert r4.status_code == 400


@pytest.mark.unit_01
async def test_t1_9_schema_has_required_columns(initialized_db):
    """T1-9: Schema has counter, state, next_check_at, first-failure columns."""
    async with aiosqlite.connect(str(initialized_db)) as db:
        async with db.execute("PRAGMA table_info(services)") as cursor:
            cols = [row[1] for row in await cursor.fetchall()]

    expected_cols = [
        "id", "name", "slug", "health_url", "owner", "interval_seconds",
        "slo_target", "enabled", "current_state", "consecutive_failures",
        "consecutive_successes", "first_failure_at", "next_check_at", "created_at"
    ]
    for col in expected_cols:
        assert col in cols, f"Missing column {col} in services table"
