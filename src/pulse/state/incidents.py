"""Incident management: persistence, one-active guard, events, ack, notes.

Follows DECISIONS.md D-02, D-03, D-09, D-11.
"""
from src.pulse.clock import clock
from src.pulse.notify.webhook import queue_delivery


async def open_incident(db, service_id: int, service_name: str, now_iso: str | None = None) -> int | None:
    """Opens one active incident for the service if none is currently active."""
    now_ts = now_iso or clock.now().isoformat()
    # Guard against duplicate active incidents
    async with db.execute(
        "SELECT id FROM incidents WHERE service_id = ? AND status = 'active'",
        (service_id,),
    ) as cursor:
        existing = await cursor.fetchone()
        if existing:
            return existing[0]

    title = f"Service {service_name} is DOWN"
    cursor = await db.execute(
        """
        INSERT INTO incidents (service_id, opened_at, status, title)
        VALUES (?, ?, 'active', ?)
        """,
        (service_id, now_ts, title),
    )
    incident_id = cursor.lastrowid
    await db.execute(
        """
        INSERT INTO incident_events (incident_id, event_type, message, created_at)
        VALUES (?, 'opened', ?, ?)
        """,
        (incident_id, f"Incident opened: {title}", now_ts),
    )
    await queue_delivery(db, incident_id, "incident_opened")  # D-28: pending row, sent by background task
    return incident_id


async def resolve_incident(db, service_id: int, now_iso: str | None = None) -> int | None:
    """Resolves active incident for the service if one exists."""
    now_ts = now_iso or clock.now().isoformat()
    async with db.execute(
        "SELECT id FROM incidents WHERE service_id = ? AND status = 'active'",
        (service_id,),
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            return None
        incident_id = row[0]

    await db.execute(
        "UPDATE incidents SET status = 'resolved', resolved_at = ? WHERE id = ?",
        (now_ts, incident_id),
    )
    await db.execute(
        """
        INSERT INTO incident_events (incident_id, event_type, message, created_at)
        VALUES (?, 'resolved', 'Service recovered to HEALTHY', ?)
        """,
        (incident_id, now_ts),
    )
    await queue_delivery(db, incident_id, "incident_resolved")  # D-28
    return incident_id


async def acknowledge_incident(
    db, incident_id: int, acknowledged_by: str = "operator", now_iso: str | None = None
) -> dict:
    """Acknowledges an active incident idempotently. Rejects if resolved."""
    now_ts = now_iso or clock.now().isoformat()
    async with db.execute(
        "SELECT id, service_id, status, acknowledged_at, acknowledged_by FROM incidents WHERE id = ?",
        (incident_id,),
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Incident {incident_id} not found")

        status, ack_at = row[2], row[3]
        if status == "resolved":
            raise ValueError("Cannot acknowledge a resolved incident")

        # Idempotent: if already acknowledged, do not insert duplicate event
        if ack_at:
            return {"id": incident_id, "acknowledged": True, "acknowledged_at": ack_at}

    await db.execute(
        "UPDATE incidents SET acknowledged_at = ?, acknowledged_by = ? WHERE id = ?",
        (now_ts, acknowledged_by, incident_id),
    )
    await db.execute(
        """
        INSERT INTO incident_events (incident_id, event_type, message, created_at)
        VALUES (?, 'acknowledged', ?, ?)
        """,
        (incident_id, f"Acknowledged by {acknowledged_by}", now_ts),
    )
    await db.commit()
    return {"id": incident_id, "acknowledged": True, "acknowledged_at": now_ts}


async def add_incident_note(
    db, incident_id: int, note: str, now_iso: str | None = None
) -> dict:
    """Appends an operator note to the incident event timeline."""
    note = note.strip()
    if not note:
        raise ValueError("Note cannot be empty")

    now_ts = now_iso or clock.now().isoformat()
    async with db.execute(
        "SELECT id, status FROM incidents WHERE id = ?", (incident_id,)
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Incident {incident_id} not found")

    await db.execute(
        """
        INSERT INTO incident_events (incident_id, event_type, message, created_at)
        VALUES (?, 'note_added', ?, ?)
        """,
        (incident_id, note, now_ts),
    )
    await db.commit()
    return {"incident_id": incident_id, "note": note, "created_at": now_ts}


async def get_incident_timeline(db, incident_id: int) -> list[dict]:
    """Returns chronological events for an incident."""
    async with db.execute(
        """
        SELECT id, incident_id, event_type, message, created_at
        FROM incident_events
        WHERE incident_id = ?
        ORDER BY id ASC
        """,
        (incident_id,),
    ) as cursor:
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "incident_id": r[1],
                "event_type": r[2],
                "message": r[3],
                "created_at": r[4],
            }
            for r in rows
        ]
