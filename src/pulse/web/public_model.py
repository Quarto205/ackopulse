"""Public-safe view model (D-10): only fields allowed on /status.

Never include: health_url, owner, internal errors, operator notes,
acknowledgement details.
"""
from src.pulse.clock import clock

STATE_LABELS = {  # D-21 collapse
    "HEALTHY": "UP",
    "DEGRADED": "ISSUE",
    "DOWN": "OUTAGE",
}


def public_service(row: dict) -> dict:
    return {
        "name": row["name"],
        "state": STATE_LABELS.get(row["current_state"], "ISSUE"),
    }


async def public_snapshot(db) -> dict:
    """Everything the public page needs, nothing more (D-10)."""
    async with db.execute(
        "SELECT id, name, current_state FROM services WHERE enabled = 1 ORDER BY name"
    ) as cur:
        services = [public_service(dict(zip(("id", "name", "current_state"), r)))
                    for r in await cur.fetchall()]

    cutoff = (clock.now() - __import__("datetime").timedelta(hours=24)).isoformat()  # D-20
    async with db.execute(
        """SELECT i.id, s.name, i.title, i.opened_at, i.resolved_at, i.status
           FROM incidents i JOIN services s ON s.id = i.service_id
           WHERE i.status = 'active'
              OR (i.status = 'resolved' AND i.opened_at >= ?)
           ORDER BY i.opened_at DESC""",
        (cutoff,),
    ) as cur:
        cols = ("id", "service_name", "title", "opened_at", "resolved_at", "status")
        incidents = [dict(zip(cols, r)) for r in await cur.fetchall()]

    return {"services": services, "incidents": incidents}
