import os
import re
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.pulse.clock import clock
from src.pulse.config import settings
from src.pulse.db import get_db, init_db
from src.pulse.main import app
from src.pulse.seed import seed_services


class FakeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/slow"):
            m = re.search(r"ms=(\d+)", self.path)
            ms = int(m.group(1)) if m else 300
            time.sleep(ms / 1000)
            self.send_response(200)
        elif self.path.startswith("/error500"):
            self.send_response(500)
        else:
            self.send_response(200)
        self.end_headers()

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def fake_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path, monkeypatch):
    """Isolate database for each test in a clean temp directory."""
    test_db = tmp_path / "test_pulse.db"
    monkeypatch.setattr(settings, "db_path", test_db)
    clock.reset()
    yield test_db
    clock.reset()


@pytest_asyncio.fixture
async def initialized_db(setup_test_env):
    """Initializes schema on the temporary test database."""
    await init_db(setup_test_env)
    return setup_test_env


@pytest_asyncio.fixture
async def seeded_db(initialized_db):
    """Initializes schema and seeds default mock services."""
    await seed_services()
    return initialized_db


@pytest_asyncio.fixture
async def async_client(initialized_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
