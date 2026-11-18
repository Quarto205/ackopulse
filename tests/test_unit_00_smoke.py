import pytest
from httpx import AsyncClient


@pytest.mark.unit_00
async def test_smoke_health(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
