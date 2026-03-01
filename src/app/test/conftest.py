import os
import pytest
from httpx import AsyncClient, ASGITransport
from dotenv import load_dotenv

load_dotenv()

# Storage credentials for S3-compatible mock; moto / localstack
os.environ.setdefault("STORAGE_REGION", "us-east-1")
os.environ.setdefault("STORAGE_BUCKET_NAME", "test-bucket")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

# Auth — disabled in tests as no real OIDC server present
os.environ.setdefault("AUTH_JWKS_URL", "")
os.environ.setdefault("AUTH_ISSUER", "")
os.environ.setdefault("AUTH_AUDIENCE", "")


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
