"""Pure state classification and transitions without I/O.

Follows DECISIONS.md D-01, D-02, D-03, D-11, D-16, D-17.
"""
from dataclasses import dataclass
from enum import StrEnum


class ServiceState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"


class Outcome(StrEnum):
    FAST_OK = "FAST_OK"
    SLOW_OK = "SLOW_OK"
    FAILED = "FAILED"
    SKIP = "SKIP"


@dataclass(frozen=True)
class Transition:
    new_state: ServiceState
    consecutive_failures: int
    consecutive_successes: int
    incident_action: str | None = None  # "open", "resolve", or None


def classify_raw_probe(
    http_status: int | None,
    latency_ms: int | None,
    error: str | None,
    degraded_threshold_ms: int = 1500,
) -> Outcome:
    """Classifies a raw HTTP probe observation into an Outcome."""
    # Failed check per D-11: any non-2xx, timeout, connection refused, or error
    if error is not None or http_status is None or not (200 <= http_status < 300):
        return Outcome.FAILED

    # HTTP 2xx: check latency
    if latency_ms is not None and latency_ms >= degraded_threshold_ms:
        return Outcome.SLOW_OK

    return Outcome.FAST_OK


def observe(
    current_state: ServiceState | str | None,
    consecutive_failures: int,
    consecutive_successes: int,
    outcome: Outcome | str,
    failures_to_down: int = 2,
    recovery_successes: int = 2,
) -> Transition:
    """Computes pure state transition and counter updates based on raw probe outcome."""
    if current_state is None:
        state = ServiceState.HEALTHY
    elif isinstance(current_state, str):
        state = ServiceState(current_state.upper())
    else:
        state = current_state

    if isinstance(outcome, str):
        outcome = Outcome(outcome.upper())

    # 1. Skipped check: leave state and counters untouched (D-13)
    if outcome == Outcome.SKIP:
        return Transition(
            new_state=state,
            consecutive_failures=consecutive_failures,
            consecutive_successes=consecutive_successes,
            incident_action=None,
        )

    # 2. Fast success (2xx < degraded_threshold_ms)
    if outcome == Outcome.FAST_OK:
        new_failures = 0
        new_successes = consecutive_successes + 1

        if state == ServiceState.HEALTHY:
            return Transition(
                new_state=ServiceState.HEALTHY,
                consecutive_failures=new_failures,
                consecutive_successes=new_successes,
                incident_action=None,
            )

        # In DEGRADED or DOWN
        if new_successes >= recovery_successes:
            return Transition(
                new_state=ServiceState.HEALTHY,
                consecutive_failures=new_failures,
                consecutive_successes=new_successes,
                incident_action="resolve",
            )
        else:
            return Transition(
                new_state=ServiceState.DEGRADED,
                consecutive_failures=new_failures,
                consecutive_successes=new_successes,
                incident_action=None,
            )

    # 3. Slow success (2xx >= degraded_threshold_ms) (D-16)
    if outcome == Outcome.SLOW_OK:
        # Breaks failure streak, but does not count toward recovery
        new_failures = 0
        new_successes = 0

        if state == ServiceState.DOWN:
            return Transition(
                new_state=ServiceState.DOWN,
                consecutive_failures=new_failures,
                consecutive_successes=new_successes,
                incident_action=None,
            )
        else:
            return Transition(
                new_state=ServiceState.DEGRADED,
                consecutive_failures=new_failures,
                consecutive_successes=new_successes,
                incident_action=None,
            )

    # 4. Failed check (non-2xx, timeout, error) (D-11, D-17)
    if outcome == Outcome.FAILED:
        new_failures = consecutive_failures + 1
        new_successes = 0

        if state == ServiceState.DOWN:
            return Transition(
                new_state=ServiceState.DOWN,
                consecutive_failures=new_failures,
                consecutive_successes=new_successes,
                incident_action=None,
            )

        # Coming from HEALTHY or DEGRADED
        if new_failures >= failures_to_down:
            return Transition(
                new_state=ServiceState.DOWN,
                consecutive_failures=new_failures,
                consecutive_successes=new_successes,
                incident_action="open",
            )
        else:
            return Transition(
                new_state=ServiceState.DEGRADED,
                consecutive_failures=new_failures,
                consecutive_successes=new_successes,
                incident_action=None,
            )

    raise ValueError(f"Unknown outcome: {outcome}")
