# src/app/test/conftest.py
import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def set_test_env_vars():
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    os.environ["COGNITO_REGION"] = "ap-northeast-2"
    os.environ["USER_POOL_ID"] = "test-pool"
    os.environ["APP_CLIENT_ID"] = "test-client"

# 테스트 파일 전체에서 사용되는 env  변수
from dotenv import load_dotenv

load_dotenv()
