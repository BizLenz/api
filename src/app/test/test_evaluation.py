# src/app/test/test_evaluation.py
# 이 파일은 사업계획서 분석(evaluation) 라우터를 테스트합니다.
# S3 다운로드 모킹을 강화해 NoSuchKey 예외를 피하고, 성공적인 다운로드를 시뮬레이션합니다.

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient  # FastAPI 테스트 클라이언트 (이전 수정 기반)
from src.app.main import app  # FastAPI 앱 임포트

# 가짜 평가 기준 데이터 (테스트용)
FAKE_EVALUATION_CRITERIA = [
    {
        "section_name": "기술성", "max_score": 30,
        "main_category": "기술성 및 사업성", "category_max_score": 70, "category_min_score": 40,
        "pillars": {
            "기술의 차별성(15점)": {
                "description": "핵심 기술/서비스의 독창성 및 차별성",
                "questions": ["기존 기술/서비스 대비 차별점은 무엇인가?"]
            }
        }
    }
]

# 모킹된 섹션 분석 응답 (Gemini AI 시뮬레이션)
mock_section_analysis_response = MagicMock()
mock_section_analysis_response.text = "### 분석 섹션: 기술성\n\n[ANALYSIS SUCCESSFUL]\n\n---"

# 모킹된 최종 리포트 JSON 문자열 (Gemini AI 응답 시뮬레이션)
final_report_json_string = json.dumps({
    "report": {
        "title": "예비창업패키지 맞춤형 사업계획서 분석 리포트", "total_score": 85,
        "summary": "기술성과 사업성 측면에서 매우 우수한 평가를 받았습니다.",
        "sections": [
            { "name": "기술성", "score": 25, "max_score": 30, "feedback": "기술의 차별성이 명확하게 드러납니다."}
        ]
    }
})
mock_final_report_response = MagicMock()
mock_final_report_response.text = final_report_json_string

# 테스트 fixture: TestClient 생성
@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_create_analysis_success(mocker, client: TestClient):
    # 모킹: S3 다운로드 함수 (NoSuchKey 예외 피하기 위해 가짜 파일 내용 반환)
    mocker.patch(
        "src.app.routers.evaluation._s3.download_file",
        return_value=b"PDF file content bytes"  # 가짜 PDF 바이트 데이터 반환 (다운로드 성공 시뮬레이션)
    )
    
    # 모킹: Gemini AI 구성
    mocker.patch("src.app.routers.evaluation.genai.configure", return_value=None)
    
    # 모킹: 파일 업로드 (Gemini AI에 PDF 업로드 시뮬레이션)
    mock_uploaded_file = MagicMock()
    mocker.patch("src.app.routers.evaluation.genai.upload_file", return_value=mock_uploaded_file)
    
    # 모킹: Gemini 모델 인스턴스 (비동기 콘텐츠 생성 시뮬레이션)
    mock_model_instance = MagicMock()
    mock_model_instance.generate_content_async = AsyncMock(
        side_effect=[mock_section_analysis_response, mock_final_report_response]
    )
    mocker.patch("src.app.routers.evaluation.genai.GenerativeModel", return_value=mock_model_instance)
    
    # 모킹: 평가 기준 데이터
    mocker.patch("src.app.routers.evaluation.EVALUATION_CRITERIA", FAKE_EVALUATION_CRITERIA)

    # POST 요청 (TestClient 사용)
    request_payload = {
        "s3_key": "user-uploads/some-id/plan.pdf",  # S3 키 (모킹으로 성공 처리)
        "contest_type": "예비창업패키지",
        "json_model": "gemini-1.5-flash",
        "timeout_sec": 600
    }
    response = client.post("/api/v1/analysis/request", json=request_payload)

    # 응답 검증 (84번째 줄: status_code == 201 확인)
    assert response.status_code == 201  # 성공 응답 코드 확인
    response_data = response.json()
    assert response_data["contest_type"] == "예비창업패키지"
    assert response_data["sections_analyzed"] == len(FAKE_EVALUATION_CRITERIA)
    report_json_dict = json.loads(response_data["report_json"])
    expected_json_dict = json.loads(final_report_json_string)
    assert report_json_dict == expected_json_dict
