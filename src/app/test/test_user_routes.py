from __future__ import annotations
from typing import Any, Dict
import pytest 
from fastapi.testclient import TestClient 

from main import app
from app.database import get_db
from app.services import auth_service
from datetime import datetime, timezone

@pytest.fixture()
def fake_db_session():
    """
    - 실제 SQLAlchemy Session 대신 사용하는 테스트용 파일
    - 필요한 최소한의 속성만 제공하여 의존성 해결에 사용
    """
    class FakeSession:
        def __init__(self) -> None:
            self._committed = False

        # 실제 코드에서 사용하지 않으면 pass
        def commit(self) -> None:
            self._committed = True
        
        def rollback(self) -> None:
            self._committed = False

        def close(self) -> None:
            return 
        
    return FakeSession()


@pytest.fixture()
def fake_auth_service(monkeypatch):
    """
    - 라우터가 사용하는 auth_service.ensure_profile/get_profile/add_token_usage 함수를
      테스트 더블로 교체하여 DB 없이도 예측 가능한 응답을 반환합니다.
    - 각 함수는 UserOut에 해당하는 dict 또는 모델 호환 객체를 리턴합니다.
    """
    def make_user(sub:str, tokens: int =0) -> Dict[str,Any]:
        created = datetime(2024,1,1,0,0,0,tzinfo=timezone.utc)
        return {
            "id":1,
            "cognito_sub":sub,
            "created_at":created.isoformat(),
            "total_token_usage": tokens,
        }
    def ensure_profile(db,sub:str):
        # 신규 생성 또는 upsert된 사용자 반환 가정
        return make_user(sub,token=0)

    def get_profile(db,sub:str):
        # 사용자 존재한다고 가정하고 기본 사용량 10으로 반환
        return make_user(sub, token=10)
    
    def add_token_usage(db,sub:str, inc:int):
        # 기존 10에서 inc만큼 증가한 값 반환
        return make_user(sub, token = 10+inc)
    
    monkeypatch.setattr(auth_service,"ensure_profile",ensure_profile)
    monkeypatch.setattr(auth_service,"get_profile",get_profile)
    monkeypatch.setattr(auth_service,"add_token_usage",add_token_usage)
    return True

@pytest.fixture(autouse=True)
def override_dependencies(fake_db_session):
    """
    - 모든 테스트에 대해 FastAPI의 get_db 의존성을 가짜 세션으로 교체합니다.
    - 테스트 종료 후 원복합니다.
    """
    original = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: fake_db_session
    yield
    if original is not None:
        app.dependency_overrides[get_db] = original
    else:
        app.dependency_overrides.pop(get_db,None)
    
@pytest.fixture(scope="module")
def client():
    """
    - 모듈 범위에서 재사용하는 TestClient입니다.
    - 실제 서버를 띄우지 않고 WSGI 레벨에서 FastAPI 앱을 직접 호출합니다.
    """
    with TestClient(app) as C:
        yield C     

def test_signup_unauthorized_without_header(client, fake_auth_service):
    """
    케이스:
    - x-cognito-sub 헤더가 없으면 401을 반환해야 합니다.
    - 라우터의 헤더 검증 로직이 Missing x-cognito-sub 메시지를 포함하는지 확인합니다.
    """
    resp = client.patch("/signup", json={})
    assert resp.status_code == 401, resp.text
    body = resp.json()
    assert "x-cognito-sub" in body.get("detail", ""), body

def test_signup_ok_with_header(client, fake_auth_service):
    """
    케이스:
    - x-cognito-sub 헤더가 있을 경우 200 + UserOut 형태로 반환합니다.
    """
    headers = {"x-cognito-sub": "user-sub-123"}
    resp = client.patch("/signup", json={}, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == 1
    assert data["cognito_sub"] == "user-sub-123"
    assert data["total_token_usage"] == 0
    assert "created_at" in data and data["created_at"]

def test_get_my_profile_requires_header(client, fake_auth_service):
    """
    케이스:
    - GET /users/me는 x-cognito-sub 헤더가 필수입니다.
    - FastAPI의 Header(..., ...) 유효성에 의해 미제공 시 422가 발생하는 것이 일반적입니다.
    """
    resp = client.get("/users/me")
    assert resp.status_code in (400, 401, 422), resp.text

def test_get_my_profile_ok(client, fake_auth_service):
    """
    케이스:
    - x-cognito-sub 헤더를 제공하면 UserOut을 반환합니다.
    """
    headers = {"x-cognito-sub": "me-sub-999"}
    resp = client.get("/users/me", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["cognito_sub"] == "me-sub-999"
    assert data["total_token_usage"] == 10
    assert "id" in data and "created_at" in data

def test_increase_token_usage_validation(client, fake_auth_service):
    """
    케이스:
    - inc 쿼리 파라미터는 gt=0 제약이 있으므로 0 또는 음수면 422가 발생합니다.
    """
    headers = {"x-cognito-sub": "me-sub-999"}
    resp = client.post("/users/me/token-usage?inc=0", headers=headers)
    assert resp.status_code == 422, resp.text

    resp = client.post("/users/me/token-usage?inc=-1", headers=headers)
    assert resp.status_code == 422, resp.text

def test_increase_token_usage_ok(client, fake_auth_service):
    """
    케이스:
    - inc가 양수일 때 누적 사용량(total_token_usage)이 증가한 UserOut을 반환합니다.
    """
    headers = {"x-cognito-sub": "me-sub-999"}
    resp = client.post("/users/me/token-usage?inc=7", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["cognito_sub"] == "me-sub-999"
    assert data["total_token_usage"] == 17  # 10 + 7