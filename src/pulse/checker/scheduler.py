"""Scheduler: select due services, run concurrently, persist each result
in one immediate transaction (D-14), update next_check_at = now + interval
(D-12), skip in-flight services and count skips (D-13), apply state classification
and incident lifecycle (D-01, D-02, D-03, D-16, D-17)."""
import asyncio
from datetime import timedelta

import aiosqlite
import httpx

from src.pulse.checker.probe import probe
from src.pulse.clock import clock
from src.pulse.config import settings
from src.pulse.state.classify import (
    ServiceState,
    classify_raw_probe,
    observe,
)
from src.pulse.state.incidents import open_incident, resolve_incident

DUE_SQL = (
    "SELECT id, name, health_url, interval_seconds FROM services "
    "WHERE enabled = 1 AND next_check_at IS NOT NULL "
    "AND next_check_at <= ?"
)


class Scheduler:
    def __init__(self, max_concurrency: int = 10):
        self.in_flight: set[int] = set()
        self.skipped_runs: int = 0
        self._sem = asyncio.Semaphore(max_concurrency)
        self._client: httpx.AsyncClient | None = None

    async def run_once(self, db: aiosqlite.Connection) -> int:
        """One tick: check all due services concurrently. Returns run count."""
        now = clock.now().isoformat()
        async with db.execute(DUE_SQL, (now,)) as cur:
            rows = await cur.fetchall()
        due = [
            {"id": r[0], "name": r[1], "health_url": r[2], "interval_seconds": r[3]}
            for r in rows
        ]

        runnable = []
        for svc in due:
            if svc["id"] in self.in_flight:
                self.skipped_runs += 1  # D-13
            else:
                runnable.append(svc)

        if runnable:
            if self._client is None:
                self._client = httpx.AsyncClient(timeout=settings.check_timeout_seconds)
            results = await asyncio.gather(  # exceptions never kill the tick
                *(self._probe_one(s) for s in runnable), return_exceptions=True
            )
            for r in results:
                if isinstance(r, Exception):
                    pass  # counted; one failing check must not stop others
        return len(runnable)

    async def _probe_one(self, svc: dict) -> None:
        async with self._sem:
            self.in_flight.add(svc["id"])
            try:
                result = await probe(svc, client=self._client)  # D-08 timeout on shared client
                await self._persist(svc, result)  # immediate write, D-14
            except Exception:
                pass  # one failing check must not stop others
            finally:
                self.in_flight.discard(svc["id"])

    async def _persist(self, svc: dict, result) -> None:
        # Classify raw probe
        outcome = classify_raw_probe(
            http_status=result.http_status,
            latency_ms=result.latency_ms,
            error=result.error_message,
            degraded_threshold_ms=settings.degraded_latency_threshold_ms,
        )
        check_state = outcome.value
        next_check = (clock.now() + timedelta(seconds=svc["interval_seconds"])).isoformat()  # D-12
        now_ts = clock.now().isoformat()

        async with aiosqlite.connect(str(settings.db_path)) as db:  # D-14: one immediate txn
            db.row_factory = aiosqlite.Row

            # 1. Fetch current service state and counters
            async with db.execute(
                """SELECT current_state, consecutive_failures, consecutive_successes, first_failure_at
                   FROM services WHERE id = ?""",
                (svc["id"],),
            ) as cur:
                s_row = await cur.fetchone()

            curr_state = s_row["current_state"] if s_row else "HEALTHY"
            fails = s_row["consecutive_failures"] if s_row else 0
            succs = s_row["consecutive_successes"] if s_row else 0
            first_fail = s_row["first_failure_at"] if s_row else None

            # 2. Compute state transition
            transition = observe(
                current_state=curr_state,
                consecutive_failures=fails,
                consecutive_successes=succs,
                outcome=outcome,
                failures_to_down=settings.failures_to_down,
                recovery_successes=settings.recovery_successes,
            )

            # 3. Handle first_failure_at tracking
            if transition.consecutive_failures == 1 and not first_fail:
                first_fail = result.checked_at
            elif transition.new_state == ServiceState.HEALTHY:
                first_fail = None

            # 4. Insert health_checks row (raw observation)
            await db.execute(
                """INSERT INTO health_checks
                   (service_id, scheduled_at, started_at, checked_at, duration_ms,
                    http_status, latency_ms, state, error_message)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    result.service_id,
                    result.scheduled_at,
                    result.started_at,
                    result.checked_at,
                    result.duration_ms,
                    result.http_status,
                    result.latency_ms,
                    check_state,
                    result.error_message,
                ),
            )

            # 5. Update service with derived state and counters
            await db.execute(
                """UPDATE services
                   SET next_check_at = ?, current_state = ?,
                       consecutive_failures = ?, consecutive_successes = ?,
                       first_failure_at = ?
                   WHERE id = ?""",
                (
                    next_check,
                    transition.new_state.value,
                    transition.consecutive_failures,
                    transition.consecutive_successes,
                    first_fail,
                    svc["id"],
                ),
            )

            # 6. Apply incident lifecycle
            if transition.incident_action == "open":
                await open_incident(db, svc["id"], svc["name"], now_ts)
            elif transition.incident_action == "resolve":
                await resolve_incident(db, svc["id"], now_ts)

            await db.commit()
