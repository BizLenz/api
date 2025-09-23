# src/app/test/conftest.py
import os
import pytest
from httpx import AsyncClient, ASGITransport
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("S3_BUCKET", "test-bucket")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def app_instance():
    from app.main import app

    return app


@pytest.fixture
async def client(app_instance):
    async with AsyncClient(
        transport=ASGITransport(app=app_instance), base_url="http://test"
    ) as ac:
        yield ac