# src/app/test/test_evaluation.py
# 이 파일은 evaluation 라우터의 API 엔드포인트를 테스트합니다.
# Pytest를 사용하며, mocking을 통해 외부 서비스(S3, Gemini AI)를 시뮬레이션합니다.
# 초보 개발자를 위해 각 테스트 함수에 목적과 mocking 이유를 주석으로 설명합니다.

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from botocore.exceptions import ClientError
from src.main import app  # main.py에서 FastAPI 앱을 import (프로젝트 구조에 맞게 조정)

# TestClient 초기화: FastAPI 앱을 테스트 모드로 로드
client = TestClient(app)

# 기본 요청 데이터: AnalysisCreateIn 스키마에 맞춤 (file_path 포함)
BASE_JSON_DATA = {
    "contest_type": "예비창업패키지",
    "file_path": "mock/path/mock.pdf",  # file_path 사용: S3 키 시뮬레이션
    "analysis_model": "gemini-2.5-flash",
    "json_model": "gemini-2.5-flash",
    "timeout_sec": 60
}

# 성공 케이스 테스트: 분석 요청이 정상적으로 처리되는지 확인
@pytest.mark.asyncio
@patch("app.routers.evaluation._s3.download_file")  # S3 다운로드 mocking
@patch("app.routers.evaluation.genai.upload_file_async", new_callable=AsyncMock)  # Gemini 파일 업로드 mocking
@patch("app.routers.evaluation.genai.GenerativeModel.generate_content_async", new_callable=AsyncMock)  # Gemini 콘텐츠 생성 mocking (2번 호출: 섹션 분석 + 최종 보고서)
async def test_create_analysis_success(
    mock_generate_content_async,
    mock_upload_file_async,
    mock_download_file
):
    """
    목적: 정상적인 분석 요청 시 201 상태 코드와 응답 구조를 확인합니다.
    mocking 이유: 실제 S3/Gemini 호출을 피하고, 테스트를 빠르게 실행하기 위함.
    """
    # S3 다운로드 성공 시뮬레이션
    mock_download_file.return_value = None

    # Gemini 업로드 파일 mocking
    mock_upload_file_async.return_value = MagicMock(file_name="mock.pdf")

    # Gemini generate_content_async mocking: 첫 번째 호출(섹션 분석), 두 번째 호출(최종 보고서)
    mock_generate_content_async.side_effect = [
        AsyncMock(text="Test analysis section"),  # 섹션 분석 응답
        AsyncMock(text='{"final_report": true}')   # 최종 JSON 보고서 응답
    ]

    # API 호출
    response = client.post("/request", json=BASE_JSON_DATA)

    # 결과 확인
    assert response.status_code == 201
    assert "report_json" in response.json()
    assert response.json()["sections_analyzed"] > 0  # 분석된 섹션 수 확인
    assert response.json()["contest_type"] == BASE_JSON_DATA["contest_type"]

# S3 404 에러 케이스 테스트: 파일이 없을 때 404 반환 확인
@pytest.mark.asyncio
@patch("app.routers.evaluation._s3.download_file")  # S3 다운로드 mocking
async def test_create_analysis_s3_not_found(mock_download_file):
    """
    목적: S3에서 파일을 찾을 수 없을 때 (404/NoSuchKey) HTTP 404를 반환하는지 확인합니다.
    mocking 이유: 실제 S3 에러를 시뮬레이션하여 예외 처리 로직 테스트.
    """
    # S3 다운로드 에러 mocking: ClientError with '404' code
    error_response = {"Error": {"Code": "404"}}
    mock_download_file.side_effect = ClientError(error_response, "download_file")

    # API 호출
    response = client.post("/request", json=BASE_JSON_DATA)

    # 결과 확인
    assert response.status_code == 404
    assert "S3 객체를 찾을 수 없습니다." in response.json()["detail"]

# 타임아웃 에러 케이스 테스트: 분석 시간이 초과할 때 504 반환 확인
@pytest.mark.asyncio
@patch("app.routers.evaluation._s3.download_file")  # S3 다운로드 mocking
@patch("app.routers.evaluation.genai.upload_file_async", new_callable=AsyncMock)  # Gemini 업로드 mocking
@patch("app.routers.evaluation.asyncio.gather", new_callable=AsyncMock)  # asyncio.gather mocking for timeout
async def test_create_analysis_timeout(
    mock_gather,
    mock_upload_file_async,
    mock_download_file
):
    """
    목적: 분석 타임아웃 시 HTTP 504를 반환하는지 확인합니다.
    mocking 이유: asyncio.wait_for의 타임아웃을 시뮬레이션.
    """
    # S3 다운로드 성공
    mock_download_file.return_value = None

    # Gemini 업로드 성공
    mock_upload_file_async.return_value = MagicMock(file_name="mock.pdf")

    # asyncio.gather 타임아웃 에러 시뮬레이션
    mock_gather.side_effect = asyncio.TimeoutError()

    # API 호출
    response = client.post("/request", json=BASE_JSON_DATA)

    # 결과 확인
    assert response.status_code == 504
    assert "분석 타임아웃" in response.json()["detail"]

# 추가: DB 관련 엔드포인트 테스트 (create_result_endpoint 예시)
@pytest.mark.asyncio
@patch("app.crud.evaluation.create_analysis_result")  # CRUD 함수 mocking
async def test_create_result_endpoint(mock_create_analysis_result):
    """
    목적: 분석 결과 기록 엔드포인트가 정상 동작하는지 확인합니다.
    mocking 이유: 실제 DB 접근을 피함.
    """
    # mocking 반환값: 가짜 AnalysisResultOut 객체
    mock_create_analysis_result.return_value = MagicMock(
        analysis_job_id=1,
        evaluation_type="test",
        score=90.0,
        summary="Test summary",
        details="Test details"
    )

    # 요청 데이터
    json_data = {
        "analysis_job_id": 1,
        "evaluation_type": "test",
        "score": 90.0,
        "summary": "Test summary",
        "details": "Test details"
    }

    # API 호출
    response = client.post("/record", json=json_data)

    # 결과 확인
    assert response.status_code == 201
    assert response.json()["score"] == 90.0
