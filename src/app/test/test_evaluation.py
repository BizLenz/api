# src/app/test/routers/test_evaluation.py
# 이 파일은 /request 엔드포인트의 단위 테스트를 정의합니다.
# FastAPI TestClient를 사용하여 API를 호출하고, 외부 의존성을 모킹합니다.
# 비동기 테스트를 위해 pytest-asyncio를 사용합니다.
# 테스트 목적: 분석 요청이 성공적으로 처리되고 DB에 저장되는지 확인.
# 수정: main.py prefix="/" 설정에 맞춰 경로 유지, 인증 의존성 오버라이드 강화.

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json

# FastAPI 앱 및 관련 임포트
from app.main import (
    app,
)  # app/main.py에 있는 FastAPI app을 임포트 (Mangum 핸들러와 연동됨)
from app.routers.evaluation import (
    require_scope,
)  # evaluation 라우터와 의존성 임포트
from app.prompts.yeobi_startup import EVALUATION_CRITERIA  # 섹션 수 확인용

# TestClient 생성: 전체 app 사용 (prefix="/"이므로 /request 직접 접근)
client = TestClient(app)


# 수정: 인증 의존성 오버라이드 (openid scope를 모킹하여 404/인증 오류 방지)
def mock_require_scope(scope: str):
    return True  # 가짜로 인증 통과 반환 (실제 Cognito 호출 무시)


app.dependency_overrides[require_scope] = (
    mock_require_scope  # require_scope 함수 오버라이드
)

# 테스트용 더미 데이터: Gemini AI가 반환할 가짜 report_json
dummy_report = json.dumps(
    {
        "score": 85.5,
        "summary": "전체적으로 우수한 사업계획서입니다.",
        "details": {"section1": "상세 분석 1", "section2": "상세 분석 2"},
    }
)

# /request API 호출에 필요한 페이로드 예시 (AnalysisCreateIn 스키마에 맞춤)
request_payload = {
    "file_path": "dummy/path/to/file.pdf",  # S3 파일 경로 (모킹됨)
    "contest_type": "startup",  # 공모전 유형
    "timeout_sec": 10,  # 타임아웃 초
    "json_model": "test-model",  # 사용 모델
}


# 비동기 테스트 함수: /request 엔드포인트 테스트
@pytest.mark.asyncio  # 비동기 테스트를 위한 마커 (pytest-asyncio 필요)
@patch("app.routers.evaluation._s3")  # AWS S3 클라이언트 모킹 (boto3.client)
@patch("app.routers.evaluation.genai")  # Google Generative AI 모킹
@patch(
    "app.routers.evaluation.create_analysis_result"
)  # DB 저장 함수 모킹 (app.crud.evaluation)
async def test_create_analysis(mock_create_analysis_result, mock_genai, mock_s3):
    # S3 download_file 모킹: 실제 다운로드를 하지 않고 None 반환 (성공 시뮬레이션)
    mock_s3.download_file.return_value = None

    # genai.configure 모킹: API 키 설정을 모킹 (동기 함수)
    mock_genai.configure.return_value = None

    # genai.upload_file_async 모킹: 파일 업로드를 비동기 모킹 (AsyncMock 사용)
    mock_genai.upload_file_async = AsyncMock(
        return_value=MagicMock()
    )  # 가짜 업로드 파일 객체 반환

    # genai.GenerativeModel 모킹: 섹션 분석 모델 (여러 번 호출되므로 side_effect 사용)
    mock_model_instance = MagicMock()
    mock_model_instance.generate_content_async = AsyncMock(
        return_value=MagicMock(text="샘플 분석 텍스트")
    )

    # 최종 보고서 모델 모킹: report_json 반환
    mock_final_model_instance = MagicMock()
    mock_final_model_instance.generate_content_async = AsyncMock(
        return_value=MagicMock(text=dummy_report)
    )

    # 수정: GenerativeModel side_effect 동적 설정 (섹션 분석(EVALUATION_CRITERIA 수) + 최종 보고서 1회)
    mock_genai.GenerativeModel.side_effect = [mock_model_instance] * len(
        EVALUATION_CRITERIA
    ) + [mock_final_model_instance]

    # create_analysis_result 모킹: DB 저장 결과를 가짜로 반환 (AnalysisResultOut 스키마에 맞춤)
    mock_create_analysis_result.return_value = {
        "result_id": 123,  # 가짜 result_id
        "score": 85.5,
        "summary": "전체적으로 우수한 사업계획서입니다.",
        "details": dummy_report,  # JSON 문자열
    }

    # TestClient로 POST 요청 보내기: prefix="/"이므로 /request 직접 사용
    response = client.post("/request", json=request_payload)

    # 응답 검증: 상태 코드와 JSON 내용 확인
    assert response.status_code == 201  # HTTP 201 Created 기대
    json_resp = response.json()
    assert json_resp["result_id"] == 123  # 저장된 result_id 확인
    assert json_resp["score"] == 85.5  # 점수 확인
    assert json_resp["summary"] == "전체적으로 우수한 사업계획서입니다."  # 요약 확인

    # 모킹 함수 호출 확인: 올바른 인수로 호출되었는지 검증
    mock_s3.download_file.assert_called_once()  # S3 다운로드 1회 호출 확인
    mock_genai.upload_file_async.assert_awaited_once()  # 파일 업로드 비동기 호출 확인
    mock_create_analysis_result.assert_called_once()  # DB 저장 1회 호출 확인