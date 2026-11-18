"""Helper script to run all pulse starter-kit mock services and webhook receiver locally.

Starts:
- quotes on port 7001
- payments on port 7002
- claims on port 7003
- notifications on port 7004
- webhook-receiver on port 9900
"""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOCK_DIR = ROOT / "pulse-starter-kit" / "mock-service"
WEBHOOK_DIR = ROOT / "pulse-starter-kit" / "webhook-receiver"

SERVICES = [
    {"name": "quotes", "port": "7001", "cwd": MOCK_DIR, "file": "app.py"},
    {"name": "payments", "port": "7002", "cwd": MOCK_DIR, "file": "app.py"},
    {"name": "claims", "port": "7003", "cwd": MOCK_DIR, "file": "app.py"},
    {"name": "notifications", "port": "7004", "cwd": MOCK_DIR, "file": "app.py"},
    {"name": "webhook-receiver", "port": "9900", "cwd": WEBHOOK_DIR, "file": "app.py"},
]


def main():
    processes = []
    print("Starting Pulse starter-kit services...")
    try:
        for s in SERVICES:
            env = os.environ.copy()
            env["PORT"] = s["port"]
            env["SERVICE_NAME"] = s["name"]
            p = subprocess.Popen(
                [sys.executable, str(s["cwd"] / s["file"])],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            processes.append((s["name"], p, s["port"]))
            print(f"  [STARTED] {s['name']} listening on http://localhost:{s['port']}")

        print("\nAll 4 mock services + webhook receiver running.")
        print("Press Ctrl+C to stop all services.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping all services...")
    finally:
        for name, p, port in processes:
            p.terminate()
            p.wait()
        print("All starter kit services stopped.")


if __name__ == "__main__":
    main()
