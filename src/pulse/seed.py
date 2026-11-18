import os
from datetime import datetime, timezone
from src.pulse.clock import clock
from src.pulse.db import get_db

DEFAULT_SERVICES = [
    {
        "name": "Quotes Service",
        "slug": "quotes",
        "health_url": os.environ.get("QUOTES_HEALTH_URL", "http://localhost:7001/health"),
        "owner": "quotes-team@acko.com",
        "interval_seconds": 10,
        "slo_target": 99.9,
    },
    {
        "name": "Payments Service",
        "slug": "payments",
        "health_url": os.environ.get("PAYMENTS_HEALTH_URL", "http://localhost:7002/health"),
        "owner": "payments-team@acko.com",
        "interval_seconds": 10,
        "slo_target": 99.9,
    },
    {
        "name": "Claims Service",
        "slug": "claims",
        "health_url": os.environ.get("CLAIMS_HEALTH_URL", "http://localhost:7003/health"),
        "owner": "claims-team@acko.com",
        "interval_seconds": 10,
        "slo_target": 99.9,
    },
    {
        "name": "Notifications Service",
        "slug": "notifications",
        "health_url": os.environ.get("NOTIFICATIONS_HEALTH_URL", "http://localhost:7004/health"),
        "owner": "notifications-team@acko.com",
        "interval_seconds": 10,
        "slo_target": 99.9,
    },
]


async def seed_services(db_conn=None):
    """Idempotently seeds the 4 mock services into the database."""
    now_iso = clock.now().isoformat()

    async def _do_seed(db):
        for s in DEFAULT_SERVICES:
            # Check if exists by slug or name
            async with db.execute(
                "SELECT id FROM services WHERE slug = ? OR name = ? OR health_url = ?",
                (s["slug"], s["name"], s["health_url"]),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    await db.execute(
                        """
                        INSERT INTO services (
                            name, slug, health_url, owner, interval_seconds, 
                            slo_target, enabled, current_state, consecutive_failures, 
                            consecutive_successes, next_check_at, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, 1, 'HEALTHY', 0, 0, ?, ?)
                        """,
                        (
                            s["name"],
                            s["slug"],
                            s["health_url"],
                            s["owner"],
                            s["interval_seconds"],
                            s["slo_target"],
                            now_iso,
                            now_iso,
                        ),
                    )
        await db.commit()

    if db_conn:
        await _do_seed(db_conn)
    else:
        async with get_db() as db:
            await _do_seed(db)
