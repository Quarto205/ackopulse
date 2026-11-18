"""Webhook sender: background task polling pending deliveries (D-28).

D-23: 3 attempts, fixed 2 s delay (injectable for tests).
D-24: idempotency key `{incident_id}:{event_type}`; only 'pending' rows sent.
"""
import asyncio
from datetime import datetime, timezone

import aiosqlite
import httpx

from src.pulse.clock import clock
from src.pulse.config import settings


def build_payload(incident_id: int, event_type: str, service_name: str,
                  state: str, timestamp: str, message: str) -> dict:
    """D-06 payload shape."""
    return {
        "event": event_type,
        "incident_id": incident_id,
        "service": service_name,
        "state": state,
        "timestamp": timestamp,
        "message": message,
    }


async def queue_delivery(db, incident_id: int, event_type: str) -> None:
    """Insert a pending delivery row once per logical event (D-24).

    Called in the check/incident transaction path — never sends.
    """
    key = f"{incident_id}:{event_type}"
    await db.execute(
        """INSERT OR IGNORE INTO webhook_deliveries
           (incident_id, event_type, attempt, outcome, idempotency_key, created_at)
           VALUES (?, ?, 0, 'pending', ?, ?)""",
        (incident_id, event_type, key, clock.now().isoformat()),
    )


class WebhookSender:
    def __init__(self, retry_delay: float = 2.0, max_attempts: int = 3):
        self.retry_delay = retry_delay  # D-23
        self.max_attempts = max_attempts

    async def poll_once(self, db: aiosqlite.Connection) -> int:
        """One pass: send all pending rows. Returns attempted count."""
        async with db.execute(
            """SELECT d.id, d.attempt, d.idempotency_key, d.event_type,
                      i.service_id, s.name, s.current_state
               FROM webhook_deliveries d
               JOIN incidents i ON i.id = d.incident_id
               JOIN services s ON s.id = i.service_id
               WHERE d.outcome = 'pending'"""
        ) as cur:
            rows = await cur.fetchall()

        for rid, attempt, key, event_type, _sid, name, state in rows:
            payload = build_payload(
                incident_id=key.split(":")[0] and int(key.split(":")[0]),
                event_type=event_type,
                service_name=name,
                state=state,
                timestamp=clock.now().isoformat(),
                message=f"{event_type.replace('_', ' ')}: {name} is {state}",
            )
            attempt += 1
            outcome, code = "pending", None
            for attempt_no in range(1, self.max_attempts + 1):
                attempt = attempt_no
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.post(settings.webhook_url, json=payload)
                    code = resp.status_code
                    if resp.status_code < 300:
                        outcome = "delivered"
                        break
                    outcome = "pending"
                except Exception:
                    code = None
                    outcome = "pending"
                if attempt_no < self.max_attempts:
                    await asyncio.sleep(self.retry_delay)
            if outcome != "delivered" and attempt >= self.max_attempts:
                outcome = "failed"

            await db.execute(
                "UPDATE webhook_deliveries SET outcome = ?, attempt = ?, response_code = ?"
                " WHERE id = ?",
                (outcome, attempt, code, rid),
            )
        await db.commit()
        return len(rows)

    async def run_forever(self, interval: float = 1.0):
        """Background loop (D-28). Own DB connection; never in the check path."""
        while True:
            try:
                async with aiosqlite.connect(str(settings.db_path)) as db:
                    await self.poll_once(db)
            except Exception:
                pass
            await asyncio.sleep(interval)
