# src/app/test/test_user_routes.py

import os
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status
from unittest.mock import patch, AsyncMock
from app.main import app

# ✅ 환경변수 먼저 설정
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["COGNITO_REGION"] = "ap-northeast-2"
os.environ["USER_POOL_ID"] = "test-pool"
os.environ["APP_CLIENT_ID"] = "test-client"

# ✅ transport 객체 미리 생성
transport = ASGITransport(app=app)

# 회원가입 테스트
@pytest.mark.asyncio
@patch("app.routers.users.cognito_client.sign_up")
async def test_signup_user(mock_sign_up):
    mock_sign_up.return_value = {"UserSub": "fake-user-sub-id"}

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/auth/signup", json={"email": "test@example.com", "password": "password123!"}
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"
    assert "user_sub" in response.json()


# 로그인 테스트 - JWT 검증 모킹
@pytest.mark.asyncio
@patch("app.routers.users.jwt.decode")
@patch("app.routers.users.get_public_keys", new_callable=AsyncMock)
async def test_login_user(mock_get_keys, mock_jwt_decode):
    mock_get_keys.return_value = {
        "keys": [{"kid": "1234", "kty": "RSA", "use": "sig", "n": "abc", "e": "AQAB"}]
    }
    mock_jwt_decode.return_value = {"sub": "user-id", "email": "test@example.com"}

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/auth/login", json={"credentials": "fake.jwt.token"})

    assert response.status_code == 200
    assert response.json()["status"] == "success"


# 비밀번호 재설정 요청
@pytest.mark.asyncio
@patch("app.routers.users.cognito_client.forgot_password")
async def test_forgot_password(mock_forgot_password):
    mock_forgot_password.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/auth/forgot-password",
            json={
                "email_info": "test@example.com",
                "confirmation_code": "123456",
                "new_password": "new-password123!",
            },
        )

    assert response.status_code == 200
    assert "message" in response.json()


# 비밀번호 재설정 완료
@pytest.mark.asyncio
@patch("app.routers.users.cognito_client.confirm_forgot_password")
async def test_reset_password(mock_reset):
    mock_reset.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/auth/reset-password",
            json={
                "email_info": "test@example.com",
                "confirmation_code": "123456",
                "new_password": "new-password123!",
            },
        )

    assert response.status_code == 200
    assert "message" in response.json()
