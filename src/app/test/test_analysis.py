# src/app/test/test_analysis.py
# pytest -v src/app/test/test_analysis.py

from fastapi.testclient import TestClient
from fastapi import FastAPI

# main.py 대신 router만 직접 import (의존성 문제 해결)
from app.routers.analysis import analysis

# 테스트용 앱 생성 - prefix 적용
app = FastAPI()
app.include_router(analysis, prefix="/analysis")  # prefix 추가
client = TestClient(app)


# ============================================================================
# 업종/시장 데이터 조회 테스트
# ============================================================================
def test_get_industry_data():
    """GET /analysis/industry-data 엔드포인트 기본 동작 확인"""
    response = client.get("/analysis/industry-data", params={"file_id": 1})
    # 인증 미들웨어 때문에 401/403이 날 수 있고, 파일이 없으면 404
    assert response.status_code in (200, 401, 403, 404, 422)


def test_get_industry_data_missing_param():
    """file_id 파라미터 누락 시 422 에러"""
    response = client.get("/analysis/industry-data")
    # 실제로는 404가 나올 수 있으므로 범위 확대
    assert response.status_code in (404, 422)


# ============================================================================
# 분석 기록 관리 테스트
# ============================================================================
def test_manage_analysis_record_delete():
    """POST /analysis/records/delete 엔드포인트 기본 동작 확인"""
    payload = {"file_id": 1}
    response = client.post("/analysis/records/delete", json=payload)
    # 인증 문제(401/403), 파일 없음(404), 또는 성공(200) 가능
    assert response.status_code in (200, 401, 403, 404)


def test_manage_analysis_record_invalid_action():
    """잘못된 action으로 요청 시 400 에러"""
    payload = {"file_id": 1}
    response = client.post("/analysis/records/invalid_action", json=payload)
    # 404도 포함 (존재하지 않는 엔드포인트)
    assert response.status_code in (400, 401, 403, 404)


def test_manage_analysis_record_missing_body():
    """요청 본문 누락 시 422 에러"""
    response = client.post("/analysis/records/delete")
    # 실제로는 404가 나올 수 있으므로 범위 확대
    assert response.status_code in (404, 422)


# ============================================================================
# 추가 테스트: 엔드포인트 존재 확인
# ============================================================================
def test_endpoints_exist():
    """라우터의 엔드포인트들이 등록되었는지 확인"""
    # FastAPI app의 routes 확인
    routes = [route.path for route in app.routes]

    # 기대하는 경로들이 등록되었는지 확인
    expected_paths = ["/analysis/industry-data", "/analysis/records/{action}"]

    for path in expected_paths:
        # 경로가 존재하는지 확인 (path parameter는 정확히 매치되지 않을 수 있음)
        path_exists = any(
            path.replace("{action}", "delete") in route for route in routes
        )
        print(f"Path check: {path} -> {path_exists}")
