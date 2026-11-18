import os
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from src.pulse.clock import clock
from src.pulse.config import settings
from src.pulse.db import get_db, init_db
from src.pulse.main import app
from src.pulse.seed import seed_services


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
