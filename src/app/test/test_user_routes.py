import pytest
from httpx import AsyncClient, ASGITransport
from src.app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_healthcheck():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/healthz")
        assert resp.status_code == 200
