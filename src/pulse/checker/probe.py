"""One HTTP health probe with bounded timeout (D-08) and full result capture."""
import time
from dataclasses import dataclass

import httpx

from src.pulse.clock import clock


@dataclass
class ProbeResult:
    service_id: int
    scheduled_at: str
    started_at: str
    checked_at: str
    duration_ms: int
    latency_ms: int | None
    http_status: int | None
    error_message: str | None


async def probe(service: dict, client: httpx.AsyncClient) -> ProbeResult:
    """Run one check against service["health_url"] on a shared client.

    Any exception becomes an error row; never raises (D-11 broad failure).
    """
    scheduled_at = clock.now().isoformat()
    t0 = time.monotonic()
    started_at = clock.now().isoformat()
    status: int | None = None
    error: str | None = None
    try:
        resp = await client.get(service["health_url"])
        status = resp.status_code
    except Exception as exc:  # timeout, refused, DNS — all "failed" (D-11)
        error = f"{type(exc).__name__}: {exc}"
    duration_ms = int((time.monotonic() - t0) * 1000)
    return ProbeResult(
        service_id=service["id"],
        scheduled_at=scheduled_at,
        started_at=started_at,
        checked_at=clock.now().isoformat(),
        duration_ms=duration_ms,
        latency_ms=duration_ms,  # measured even on error
        http_status=status,
        error_message=error,
    )
