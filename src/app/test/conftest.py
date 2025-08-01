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
