# src/app/test/conftest.py
import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("S3_BUCKET", "test-bucket")

# 리포지토리 루트 기준 src 경로 계산
root = Path(__file__).resolve().parents[3]  # .../api/src/app/test -> 루트까지 상위 3단
src_path = root / "src"
sys.path.insert(0, str(root))
sys.path.insert(0, str(src_path))

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
