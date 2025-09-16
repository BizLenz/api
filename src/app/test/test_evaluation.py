import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock
import json
from src.app.main import app

# --- 테스트용 가짜 데이터 및 모의 객체 설정 ---
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

mock_section_analysis_response = MagicMock()
mock_section_analysis_response.text = "### 분석 섹션: 기술성\n\n[ANALYSIS SUCCESSFUL]\n\n---"

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

@pytest.mark.asyncio
async def test_create_analysis_success(mocker):
    """ /api/v1/analysis/request 엔드포인트 성공 케이스 테스트 """

    # --- 모킹(Mocking) 설정 ---
    # src 폴더 구조에 맞게, 모든 모킹 경로 문자열 앞에 'src.'를 추가합니다.
    # 예: "app.routers.evaluation" -> "src.app.routers.evaluation"

    # 1. Boto3 S3 클라이언트 모킹
    mocker.patch("src.app.routers.evaluation._s3.download_file", return_value=None)

    # 2. Google GenAI 클라이언트 모킹
    mock_genai_client = MagicMock()
    mock_uploaded_file = MagicMock()
    mock_genai_client.files.upload_async = AsyncMock(return_value=mock_uploaded_file)
    mock_genai_client.models.generate_content_async = AsyncMock(
        side_effect=[mock_section_analysis_response, mock_final_report_response]
    )
    mocker.patch("src.app.routers.evaluation.genai.Client", return_value=mock_genai_client)

    # 3. 평가 기준 데이터 모킹
    mocker.patch("src.app.routers.evaluation.EVALUATION_CRITERIA", FAKE_EVALUATION_CRITERIA)

    # --- 테스트 실행 ---
    async with AsyncClient(app=app, base_url="http://test") as ac:
        request_payload = {
            "s3_key": "user-uploads/some-id/plan.pdf", "contest_type": "예비창업패키지",
            "json_model": "gemini-1.5-flash", "timeout_sec": 600
        }
        response = await ac.post("/api/v1/analysis/request", json=request_payload)

    # --- 결과 검증 ---
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["contest_type"] == "예비창업패키지"
    assert response_data["sections_analyzed"] == len(FAKE_EVALUATION_CRITERIA)

    report_json_dict = json.loads(response_data["report_json"])
    expected_json_dict = json.loads(final_report_json_string)
    assert report_json_dict == expected_json_dict