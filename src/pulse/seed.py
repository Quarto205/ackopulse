import os
from datetime import datetime, timezone
from src.pulse.clock import clock
from src.pulse.db import get_db


def is_in_docker() -> bool:
    return os.environ.get("IN_DOCKER") == "1" or os.path.exists("/.dockerenv")


def get_service_url(svc: str, host_port: int) -> str:
    env_var = f"{svc.upper()}_HEALTH_URL"
    if env_var in os.environ:
        return os.environ[env_var]
    if is_in_docker():
        return f"http://{svc}:8080/health"
    return f"http://localhost:{host_port}/health"


def get_default_services():
    return [
        {
            "name": "Quotes Service",
            "slug": "quotes",
            "health_url": get_service_url("quotes", 7001),
            "owner": "quotes-team@acko.com",
            "interval_seconds": 10,
            "slo_target": 99.9,
        },
        {
            "name": "Payments Service",
            "slug": "payments",
            "health_url": get_service_url("payments", 7002),
            "owner": "payments-team@acko.com",
            "interval_seconds": 10,
            "slo_target": 99.9,
        },
        {
            "name": "Claims Service",
            "slug": "claims",
            "health_url": get_service_url("claims", 7003),
            "owner": "claims-team@acko.com",
            "interval_seconds": 10,
            "slo_target": 99.9,
        },
        {
            "name": "Notifications Service",
            "slug": "notifications",
            "health_url": get_service_url("notifications", 7004),
            "owner": "notifications-team@acko.com",
            "interval_seconds": 10,
            "slo_target": 99.9,
        },
    ]


async def seed_services(db_conn=None):
    """Idempotently seeds the 4 mock services into the database."""
    now_iso = clock.now().isoformat()
    services_to_seed = get_default_services()

    async def _do_seed(db):
        for s in services_to_seed:
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
