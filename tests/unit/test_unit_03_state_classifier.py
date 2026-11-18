"""Unit 3.1 — State classifier tests (test-first).

Pure classification and transitions without I/O.
Tests all 12 test-first requirements and transition table rows.
"""
import pytest
from src.pulse.state.classify import (
    Outcome,
    ServiceState,
    Transition,
    classify_raw_probe,
    observe,
)


@pytest.mark.unit_03
def test_1_fast_successful_response():
    """1. Fast successful response: 2xx and < 1500ms from HEALTHY stays HEALTHY."""
    res = observe(
        current_state=ServiceState.HEALTHY,
        consecutive_failures=0,
        consecutive_successes=1,
        outcome=Outcome.FAST_OK,
    )
    assert res.new_state == ServiceState.HEALTHY
    assert res.consecutive_successes == 2
    assert res.consecutive_failures == 0
    assert res.incident_action is None


@pytest.mark.unit_03
def test_2_slow_successful_response():
    """2. Slow successful response: 2xx and >= 1500ms transitions HEALTHY to DEGRADED."""
    res = observe(
        current_state=ServiceState.HEALTHY,
        consecutive_failures=0,
        consecutive_successes=5,
        outcome=Outcome.SLOW_OK,
    )
    assert res.new_state == ServiceState.DEGRADED
    assert res.consecutive_failures == 0
    assert res.consecutive_successes == 0
    assert res.incident_action is None


@pytest.mark.unit_03
def test_3_first_consecutive_failed_check():
    """3. First failed check from HEALTHY transitions to DEGRADED without opening incident."""
    res = observe(
        current_state=ServiceState.HEALTHY,
        consecutive_failures=0,
        consecutive_successes=3,
        outcome=Outcome.FAILED,
    )
    assert res.new_state == ServiceState.DEGRADED
    assert res.consecutive_failures == 1
    assert res.consecutive_successes == 0
    assert res.incident_action is None


@pytest.mark.unit_03
def test_4_failure_threshold_reached_opens_incident():
    """4. Reaching failure threshold (2 consecutive failures) transitions to DOWN and opens incident."""
    res = observe(
        current_state=ServiceState.DEGRADED,
        consecutive_failures=1,
        consecutive_successes=0,
        outcome=Outcome.FAILED,
        failures_to_down=2,
    )
    assert res.new_state == ServiceState.DOWN
    assert res.consecutive_failures == 2
    assert res.consecutive_successes == 0
    assert res.incident_action == "open"


@pytest.mark.unit_03
def test_5_recovery_threshold_not_yet_reached():
    """5. First FAST_OK while DOWN transitions to intermediate DEGRADED, incident remains active."""
    res = observe(
        current_state=ServiceState.DOWN,
        consecutive_failures=3,
        consecutive_successes=0,
        outcome=Outcome.FAST_OK,
        recovery_successes=2,
    )
    assert res.new_state == ServiceState.DEGRADED
    assert res.consecutive_successes == 1
    assert res.consecutive_failures == 0
    assert res.incident_action is None


@pytest.mark.unit_03
def test_6_recovery_threshold_reached_resolves_incident():
    """6. Second FAST_OK reaches recovery threshold (2), transitions to HEALTHY and resolves incident."""
    res = observe(
        current_state=ServiceState.DEGRADED,
        consecutive_failures=0,
        consecutive_successes=1,
        outcome=Outcome.FAST_OK,
        recovery_successes=2,
    )
    assert res.new_state == ServiceState.HEALTHY
    assert res.consecutive_successes == 2
    assert res.consecutive_failures == 0
    assert res.incident_action == "resolve"


@pytest.mark.unit_03
def test_7_counter_resets():
    """7. Counter reset: failure resets successes to 0; SLOW_OK resets failures to 0."""
    # Failure resets successes
    r1 = observe(
        current_state=ServiceState.HEALTHY,
        consecutive_failures=0,
        consecutive_successes=5,
        outcome=Outcome.FAILED,
    )
    assert r1.consecutive_successes == 0
    assert r1.consecutive_failures == 1

    # SLOW_OK resets failures to 0 per D-16
    r2 = observe(
        current_state=ServiceState.DEGRADED,
        consecutive_failures=1,
        consecutive_successes=0,
        outcome=Outcome.SLOW_OK,
    )
    assert r2.consecutive_failures == 0
    assert r2.consecutive_successes == 0


@pytest.mark.unit_03
def test_8_all_permitted_transitions():
    """8. Verifies permitted transitions in transition table."""
    # HEALTHY -> DEGRADED via SLOW_OK
    assert observe(ServiceState.HEALTHY, 0, 0, Outcome.SLOW_OK).new_state == ServiceState.DEGRADED
    # HEALTHY -> DEGRADED via FAILED (first failure)
    assert observe(ServiceState.HEALTHY, 0, 0, Outcome.FAILED).new_state == ServiceState.DEGRADED
    # DEGRADED -> DOWN via 2nd FAILED
    assert observe(ServiceState.DEGRADED, 1, 0, Outcome.FAILED, failures_to_down=2).new_state == ServiceState.DOWN
    # DOWN -> DEGRADED via 1st FAST_OK
    assert observe(ServiceState.DOWN, 2, 0, Outcome.FAST_OK, recovery_successes=2).new_state == ServiceState.DEGRADED
    # DEGRADED -> HEALTHY via 2nd FAST_OK
    assert observe(ServiceState.DEGRADED, 0, 1, Outcome.FAST_OK, recovery_successes=2).new_state == ServiceState.HEALTHY


@pytest.mark.unit_03
def test_9_boundary_conditions_at_exact_thresholds():
    """9. Exact boundary values for latency and thresholds."""
    # Latency boundary: 1499ms is FAST_OK, 1500ms is SLOW_OK
    assert classify_raw_probe(200, 1499, None) == Outcome.FAST_OK
    assert classify_raw_probe(200, 1500, None) == Outcome.SLOW_OK

    # Failures boundary: failure 1 is DEGRADED, failure 2 is DOWN
    assert observe(ServiceState.HEALTHY, 0, 0, Outcome.FAILED, failures_to_down=2).new_state == ServiceState.DEGRADED
    assert observe(ServiceState.DEGRADED, 1, 0, Outcome.FAILED, failures_to_down=2).new_state == ServiceState.DOWN

    # Recovery boundary: 1 success stays DEGRADED, 2 successes resolves to HEALTHY
    assert observe(ServiceState.DOWN, 2, 0, Outcome.FAST_OK, recovery_successes=2).new_state == ServiceState.DEGRADED
    assert observe(ServiceState.DEGRADED, 0, 1, Outcome.FAST_OK, recovery_successes=2).new_state == ServiceState.HEALTHY


@pytest.mark.unit_03
def test_10_skipped_checks_do_not_affect_counters():
    """10. Skipped check leaves state and counters untouched."""
    res = observe(
        current_state=ServiceState.DEGRADED,
        consecutive_failures=1,
        consecutive_successes=0,
        outcome=Outcome.SKIP,
    )
    assert res.new_state == ServiceState.DEGRADED
    assert res.consecutive_failures == 1
    assert res.consecutive_successes == 0
    assert res.incident_action is None


@pytest.mark.unit_03
def test_11_initial_service_state():
    """11. Initial service state defaults to HEALTHY with 0/0 counters."""
    res = observe(
        current_state=None,
        consecutive_failures=0,
        consecutive_successes=0,
        outcome=Outcome.FAST_OK,
    )
    assert res.new_state == ServiceState.HEALTHY
    assert res.consecutive_failures == 0
    assert res.consecutive_successes == 1


@pytest.mark.unit_03
def test_12_repeated_classifications_are_deterministic():
    """12. Pure function: repeated classifications produce identical, consistent transitions."""
    t1 = observe(ServiceState.HEALTHY, 0, 2, Outcome.FAST_OK)
    t2 = observe(ServiceState.HEALTHY, 0, 2, Outcome.FAST_OK)
    assert t1 == t2



# ---------------------------------------------------------------- DB Integration Tests
import aiosqlite
from src.pulse.checker.scheduler import Scheduler
from tests.unit.test_unit_02_health_checks import add_service, set_due


@pytest.mark.unit_03
async def test_13_first_failure_sets_degraded_in_db(initialized_db, fake_server):
    """DB integration: First failure sets services.current_state = DEGRADED, fails = 1."""
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "s-deg", f"{fake_server}/error500")
        await set_due(db, sid)
        sched = Scheduler()
        await sched.run_once(db)

        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT current_state, consecutive_failures, consecutive_successes FROM services WHERE id = ?",
            (sid,),
        )
        row = await cur.fetchone()
        assert row["current_state"] == "DEGRADED"
        assert row["consecutive_failures"] == 1
        assert row["consecutive_successes"] == 0

        # No incident opened on first failure
        inc_cur = await db.execute("SELECT COUNT(*) FROM incidents WHERE service_id = ?", (sid,))
        assert (await inc_cur.fetchone())[0] == 0


@pytest.mark.unit_03
async def test_14_two_failures_opens_single_incident(initialized_db, fake_server):
    """DB integration: 2 consecutive failures sets DOWN and opens exactly one active incident."""
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "s-down", f"{fake_server}/error500")
        sched = Scheduler()

        # Check 1: DEGRADED
        await set_due(db, sid)
        await sched.run_once(db)

        # Check 2: DOWN
        await set_due(db, sid)
        await sched.run_once(db)

        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT current_state, consecutive_failures FROM services WHERE id = ?",
            (sid,),
        )
        row = await cur.fetchone()
        assert row["current_state"] == "DOWN"
        assert row["consecutive_failures"] == 2

        # Verify active incident created
        inc_cur = await db.execute(
            "SELECT id, status, title FROM incidents WHERE service_id = ? AND status = 'active'",
            (sid,),
        )
        inc = await inc_cur.fetchone()
        assert inc is not None
        assert inc["status"] == "active"

        # Check 3: Another failure does NOT create a duplicate active incident
        await set_due(db, sid)
        await sched.run_once(db)

        all_inc_cur = await db.execute(
            "SELECT COUNT(*) FROM incidents WHERE service_id = ? AND status = 'active'",
            (sid,),
        )
        assert (await all_inc_cur.fetchone())[0] == 1


@pytest.mark.unit_03
async def test_15_recovery_resolves_incident(initialized_db, fake_server):
    """DB integration: 2 healthy checks resolves active incident and returns state to HEALTHY."""
    async with aiosqlite.connect(initialized_db) as db:
        # Start in down mode with 2 failures
        sid = await add_service(db, "s-rec", f"{fake_server}/error500")
        sched = Scheduler()

        await set_due(db, sid)
        await sched.run_once(db)
        await set_due(db, sid)
        await sched.run_once(db)

        # Now change health_url to healthy endpoint
        await db.execute("UPDATE services SET health_url = ? WHERE id = ?", (f"{fake_server}/ok", sid))
        await db.commit()

        # Check 1: Intermediate recovery (DEGRADED, incident still active)
        await set_due(db, sid)
        await sched.run_once(db)
        db.row_factory = aiosqlite.Row
        s_row = await (await db.execute("SELECT current_state FROM services WHERE id = ?", (sid,))).fetchone()
        assert s_row["current_state"] == "DEGRADED"

        # Check 2: Full recovery (HEALTHY, incident resolved)
        await set_due(db, sid)
        await sched.run_once(db)
        s_row2 = await (await db.execute("SELECT current_state FROM services WHERE id = ?", (sid,))).fetchone()
        assert s_row2["current_state"] == "HEALTHY"

        # Incident status is resolved
        inc_row = await (await db.execute("SELECT status, resolved_at FROM incidents WHERE service_id = ?", (sid,))).fetchone()
        assert inc_row["status"] == "resolved"
        assert inc_row["resolved_at"] is not None


@pytest.mark.unit_03
async def test_16_acknowledge_and_notes(initialized_db, fake_server):
    """Incident acknowledge and notes lifecycle."""
    from src.pulse.state.incidents import acknowledge_incident, add_incident_note, get_incident_timeline
    async with aiosqlite.connect(initialized_db) as db:
        sid = await add_service(db, "s-ack", f"{fake_server}/error500")
        sched = Scheduler()
        await set_due(db, sid)
        await sched.run_once(db)
        await set_due(db, sid)
        await sched.run_once(db)

        # Get active incident
        cur = await db.execute("SELECT id FROM incidents WHERE service_id = ?", (sid,))
        inc_id = (await cur.fetchone())[0]

        # Acknowledge
        ack_res = await acknowledge_incident(db, inc_id, acknowledged_by="alice")
        assert ack_res["acknowledged"] is True

        # Add Note
        await add_incident_note(db, inc_id, "Investigating database cluster timeout.")

        # Check timeline
        timeline = await get_incident_timeline(db, inc_id)
        event_types = [e["event_type"] for e in timeline]
        assert event_types == ["opened", "acknowledged", "note_added"]

        # Resolve incident
        await db.execute("UPDATE incidents SET status = 'resolved' WHERE id = ?", (inc_id,))
        await db.commit()

        # Acknowledging resolved incident should fail
        with pytest.raises(ValueError, match="Cannot acknowledge a resolved incident"):
            await acknowledge_incident(db, inc_id)
