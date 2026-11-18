"""Pure-ish metric calculations over stored data.

D-04 window 24 h; D-25 healthy-only availability; D-26 MTTD/MTTR defs;
D-27 floored error budget. No-data -> None (renders "n/a", never 100%).
"""
from datetime import datetime, timedelta, timezone

import aiosqlite

from src.pulse.clock import clock

WINDOW = timedelta(hours=24)  # D-04

ESTIMATE_LABEL = "estimate from periodic checks"


async def availability(db: aiosqlite.Connection, service_id: int) -> float | None:
    """Percent of in-window checks that are HEALTHY (D-25)."""
    cutoff = (clock.now() - WINDOW).isoformat()
    async with db.execute(
        """SELECT COUNT(*), SUM(CASE WHEN state = 'HEALTHY' THEN 1 ELSE 0 END)
           FROM health_checks
           WHERE service_id = ? AND checked_at >= ?""",
        (service_id, cutoff),
    ) as cur:
        total, healthy = await cur.fetchone()
    if not total:
        return None
    return round(100.0 * (healthy or 0) / total, 4)


async def mttd_mttr(db: aiosqlite.Connection, service_id: int) -> tuple[float | None, float | None]:
    """D-26: MTTD = mean(opened_at - first_failure_at); MTTR = mean(resolved - opened)."""
    async with db.execute(
        "SELECT first_failure_at FROM services WHERE id = ?", (service_id,)
    ) as cur:
        row = await cur.fetchone()
    if not row or not row[0]:
        return None, None
    first_failure = datetime_from_iso(row[0])

    async with db.execute(
        """SELECT opened_at, resolved_at FROM incidents
           WHERE service_id = ? AND opened_at >= ?
             AND (status = 'resolved' OR status = 'active')""",
        (service_id, (clock.now() - WINDOW).isoformat()),
    ) as cur:
        rows = await cur.fetchall()

    mttds, mttrs = [], []
    for opened_at, resolved_at in rows:
        if opened_at:
            mttds.append((datetime_from_iso(opened_at) - first_failure).total_seconds())
        if resolved_at and opened_at:
            mttrs.append((datetime_from_iso(resolved_at) - datetime_from_iso(opened_at)).total_seconds())
    return (
        round(sum(mttds) / len(mttds), 3) if mttds else None,
        round(sum(mttrs) / len(mttrs), 3) if mttrs else None,
    )


def error_budget_remaining(availability_pct: float | None, slo_target: float) -> float | None:
    """D-27: budget = (100 - SLO) - (100 - availability), floored at 0."""
    if availability_pct is None:
        return None
    budget = (100.0 - slo_target) - (100.0 - availability_pct)
    return round(max(budget, 0.0), 4)


def datetime_from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)



async def service_metrics(db: aiosqlite.Connection, service_row: dict) -> dict:
    """Bundle per-service metrics with the estimate label (ARCHITECTURE §9)."""
    avail = await availability(db, service_row["id"])
    mttd, mttr = await mttd_mttr(db, service_row["id"])
    return {
        "id": service_row["id"],
        "name": service_row["name"],
        "current_state": service_row["current_state"],
        "slo_target": service_row["slo_target"],
        "availability": avail,
        "error_budget_remaining": error_budget_remaining(avail, service_row["slo_target"]),
        "mttd_seconds": mttd,
        "mttr_seconds": mttr,
        "estimate_label": ESTIMATE_LABEL,
    }
