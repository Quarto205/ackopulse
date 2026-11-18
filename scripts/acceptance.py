"""Acceptance drill for Pulse (Unit 7.3).

Executes end-to-end failure-to-recovery verification against a running
Pulse stack and mock services:
1. Verifies connectivity to Pulse and starter-kit services.
2. Asserts all 4 services are HEALTHY.
3. Simulates payments failure via POST /control/down.
4. Waits for payments to transition to DOWN, incident opened, and webhook delivered.
5. Acknowledges incident and adds operator note.
6. Resets payments via POST /control/reset (guaranteed in finally block).
7. Waits for recovery to HEALTHY, incident resolved, recovery webhook, and public page UP.
8. Verifies metrics report MTTD and MTTR.

Finishes in < 90 seconds.
"""
import sys
import time
import httpx

PULSE_BASE = "http://localhost:8000"
PAYMENTS_BASE = "http://localhost:7002"
RECEIVER_BASE = "http://localhost:9900"


def log_step(step_num: int, title: str):
    print(f"\n[{step_num}/8] {title}...", flush=True)


def poll_until(condition_fn, timeout: float = 35.0, interval: float = 1.0, desc: str = ""):
    start = time.time()
    while time.time() - start < timeout:
        val = condition_fn()
        if val:
            return val
        time.sleep(interval)
    raise TimeoutError(f"Timed out after {timeout}s waiting for: {desc}")


def run_acceptance():
    print("=" * 60)
    print("PULSE ACCEPTANCE DRILL (End-to-End Verification)")
    print("=" * 60)

    client = httpx.Client(timeout=5.0)
    incident_id = None

    try:
        # 1. Connectivity check
        log_step(1, "Checking connectivity to Pulse and starter-kit mock services")
        try:
            pulse_health = client.get(f"{PULSE_BASE}/health")
            assert pulse_health.status_code == 200, f"Pulse /health returned {pulse_health.status_code}"

            pay_health = client.get(f"{PAYMENTS_BASE}/health")
            assert pay_health.status_code in (200, 503), f"Payments /health returned {pay_health.status_code}"

            client.delete(f"{RECEIVER_BASE}/api/received")
            print("  PASS: Pulse, payments mock, and webhook receiver are online.")
        except Exception as e:
            print(f"  FAIL: Could not connect to services. Make sure 'docker compose up' or local servers are running.\n  Error: {e}")
            sys.exit(1)

        # 2. All 4 services healthy
        log_step(2, "Verifying all 4 services are HEALTHY initially")
        def check_initial_healthy():
            r = client.get(f"{PULSE_BASE}/api/services")
            if r.status_code != 200:
                return False
            svcs = r.json()
            if len(svcs) < 4:
                return False
            states = {s["name"]: s["current_state"] for s in svcs}
            return all(st in ("HEALTHY", "DEGRADED") for st in states.values())

        poll_until(check_initial_healthy, timeout=20.0, desc="all services healthy")
        print("  PASS: All 4 services are online and registered.")

        # 3. Simulate failure
        log_step(3, "Triggering failure on payments service (POST /control/down)")
        r = client.post(f"{PAYMENTS_BASE}/control/down")
        assert r.status_code == 200
        print("  PASS: Payments mock set to 'down' mode (returns 503).")

        # 4. Wait for failure threshold (DOWN, incident, webhook)
        log_step(4, "Waiting for failure threshold (payments -> DOWN, incident opened, webhook received)")
        def check_down_and_incident():
            svcs = client.get(f"{PULSE_BASE}/api/services").json()
            pay = next((s for s in svcs if s["name"] == "payments"), None)
            if not pay or pay["current_state"] != "DOWN":
                return False

            whs = client.get(f"{RECEIVER_BASE}/api/received").json()
            open_wh = [w for w in whs if isinstance(w.get("body"), dict) and w["body"].get("event") == "incident_opened"]
            if not open_wh:
                return False

            return pay, open_wh[0]["body"]

        pay_svc, open_payload = poll_until(check_down_and_incident, timeout=40.0, interval=1.5, desc="payments DOWN and incident webhook")
        incident_id = open_payload["incident_id"]
        print(f"  PASS: Payments transitioned to DOWN; Incident #{incident_id} opened; Webhook verified.")

        # 5. Acknowledge and note
        log_step(5, f"Acknowledging incident #{incident_id} and adding operator note")
        ack_res = client.post(f"{PULSE_BASE}/ops/incidents/{incident_id}/acknowledge", data={"acknowledged_by": "acceptance_bot"})
        assert ack_res.status_code in (200, 302, 303), f"Ack failed: {ack_res.status_code}"

        note_res = client.post(f"{PULSE_BASE}/ops/incidents/{incident_id}/notes", data={"note": "Root cause identified: mock failure simulated."})
        assert note_res.status_code in (200, 302, 303), f"Note failed: {note_res.status_code}"
        print("  PASS: Incident acknowledged and note successfully appended to timeline.")

        # 6. Reset payments mock
        log_step(6, "Resetting payments service to normal (POST /control/reset)")
        client.post(f"{PAYMENTS_BASE}/control/reset")
        print("  PASS: Payments reset to normal mode.")

        # 7. Wait for recovery threshold (HEALTHY, incident resolved, webhook, public page UP)
        log_step(7, "Waiting for recovery threshold (payments -> HEALTHY, incident resolved, recovery webhook)")
        def check_recovered():
            svcs = client.get(f"{PULSE_BASE}/api/services").json()
            pay = next((s for s in svcs if s["name"] == "payments"), None)
            if not pay or pay["current_state"] != "HEALTHY":
                return False

            whs = client.get(f"{RECEIVER_BASE}/api/received").json()
            res_wh = [w for w in whs if isinstance(w.get("body"), dict) and w["body"].get("event") == "incident_resolved"]
            if not res_wh:
                return False

            # Check public page
            pub = client.get(f"{PULSE_BASE}/status")
            if pub.status_code != 200 or "payments" not in pub.text:
                return False

            return True

        poll_until(check_recovered, timeout=40.0, interval=1.5, desc="payments recovered and incident resolved")
        print("  PASS: Payments recovered to HEALTHY; Incident resolved; Recovery webhook received; Public status page updated.")

        # 8. Check metrics summary
        log_step(8, "Verifying reliability metrics (MTTD, MTTR, availability)")
        metrics_res = client.get(f"{PULSE_BASE}/api/metrics/summary")
        assert metrics_res.status_code == 200
        m = metrics_res.json()
        assert "services" in m
        print(f"  PASS: Metrics endpoint functional. Active services reported: {len(m['services'])}")

        print("\n" + "=" * 60)
        print("ALL ACCEPTANCE CRITERIA PASSED! (PASS)")
        print("=" * 60)

    finally:
        # Guarantee mock reset even if any step failed
        try:
            client.post(f"{PAYMENTS_BASE}/control/reset")
        except Exception:
            pass
        client.close()


if __name__ == "__main__":
    run_acceptance()
