# src/app/test/test_evaluation.py
# 이 파일은 BizLenz 서비스의 /api/v1/analysis/request 엔드포인트를 테스트합니다.
# TestClient를 사용해 동기 요청을 시뮬레이션하며, 실제 S3/Gemini 호출을 모킹합니다.
# AnalysisResponse Pydantic 모델을 반환 형식으로 검증합니다.
# AWS RDS/S3 연동을 고려한 모킹: moto로 S3 버킷/파일 모킹.
# 한국어 주석으로 초보자 이해 돕기. Ruff 린팅 통과 (E501 등 준수).
# 주의: 동기 버전으로 async 문제를 피함. 모킹을 awaitable하게 수정 (오류 방지).

import logging
from unittest.mock import patch, MagicMock, AsyncMock
import moto  # S3 모킹 라이브러리 (AWS 서비스 시뮬레이션)
import boto3  # moto와 함께 AWS 클라이언트 생성

from fastapi.testclient import TestClient  # 동기 테스트 클라이언트
from fastapi import FastAPI
from ..routers.evaluation import router  # 상대 임포트: 평가 라우터 (FastAPI 라우터)
from ..schemas.evaluation import AnalysisResponse  # 상대 임포트: Pydantic 응답 모델 (RDS 스키마 기반)
from ..core.config import settings  # 상대 임포트: 설정 값 (S3 버킷 등)
from ..prompts.yeobi_startup import EVALUATION_CRITERIA  # 상대 임포트: 평가 기준 상수

# 로그 설정 (디버깅용, 테스트 시 상세 출력)
logging.basicConfig(level=logging.DEBUG)

# FastAPI 앱 생성 및 라우터 등록 (테스트 전용 앱)
app = FastAPI()
app.include_router(router)

client = TestClient(app)  # 동기 TestClient 초기화

# 모킹된 EVALUATION_CRITERIA (테스트용, 실제 값 사용)
FAKE_EVALUATION_CRITERIA = EVALUATION_CRITERIA

@moto.mock_aws  # moto로 AWS S3 모킹
def test_request_endpoint():  # 동기 def로 유지
    # moto S3 설정: 가짜 버킷 생성 및 파일 업로드 (실제 S3 호출 대신, 404 오류 방지)
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket=settings.s3_bucket_name, CreateBucketConfiguration={
        'LocationConstraint': 'ap-northeast-2'
    })  # settings에서 S3 버킷 이름 가져옴 (로그에 맞춤)
    s3.put_object(Bucket=settings.s3_bucket_name, Key="user-uploads/test/plan.pdf", Body="fake pdf content")  # 가짜 PDF 파일 업로드 모킹

    # 모킹: Gemini API 구성 (genai.configure 호출 모킹)
    with patch("app.routers.evaluation.genai.configure") as mock_configure:
        mock_configure.return_value = None  # mock_configure 사용 (F841 방지)

        # 모킹: upload_file_async (AsyncMock으로 awaitable 모킹)
        mock_uploaded_file = MagicMock()
        with patch("app.routers.evaluation.genai.upload_file_async", AsyncMock(return_value=mock_uploaded_file), create=True) as mock_upload:
            mock_upload.return_value = mock_uploaded_file  # mock_upload 사용 (F841 방지)

            # 모킹: GenerativeModel 및 generate_content_async (AsyncMock으로 awaitable 모킹 - "can't be used in await" 오류 해결)
            mock_model = MagicMock()
            mock_model.generate_content_async = AsyncMock(return_value=MagicMock(text="Fake analysis text"))
            with patch("app.routers.evaluation.genai.GenerativeModel", return_value=mock_model, create=True) as mock_gen_model:
                mock_gen_model.return_value = mock_model  # mock_gen_model 사용 (F841 방지)

                # 모킹: 최종 보고서 모델 (AsyncMock으로 awaitable 모킹)
                mock_final_model = MagicMock()
                mock_final_model.generate_content_async = AsyncMock(return_value=MagicMock(text='{"report": "Fake report"}'))
                with patch("app.routers.evaluation.genai.GenerativeModel", side_effect=[mock_model, mock_final_model], create=True):

                    # 모킹: asyncio.gather와 wait_for (AsyncMock으로 awaitable 모킹)
                    fake_results = [{"criteria": c, "analysis_text": "Fake text"} for c in FAKE_EVALUATION_CRITERIA]
                    with patch("asyncio.gather", AsyncMock(return_value=fake_results)) as mock_gather:
                        mock_gather.return_value = fake_results  # mock_gather 사용 (F841 방지)
                        with patch("asyncio.wait_for", AsyncMock(return_value=fake_results)) as mock_wait_for:
                            mock_wait_for.return_value = fake_results  # mock_wait_for 사용 (F841 방지)

                            # 동기 클라이언트로 API 호출 (TestClient 사용)
                            response = client.post(
                                "/api/v1/analysis/request",
                                json={
                                    "s3_key": "user-uploads/test/plan.pdf",
                                    "contest_type": "예비창업패키지",
                                    "json_model": "gemini-1.5-flash",
                                    "timeout_sec": 600
                                }
                            )
                            logging.debug(f"Response status: {response.status_code}, content: {response.text}")  # 디버깅 로그 출력

                            # 응답 검증 (201 예상, 실패 시 상세 메시지)
                            assert response.status_code == 201, f"Unexpected status code: {response.status_code}, details: {response.text}"

                            response_data = response.json()  # JSON 파싱

                            # AnalysisResponse 모델 검증 (Pydantic 스키마 기반, BizLenz 평가 결과 확인)
                            assert "report_json" in response_data  # report_json 필드 존재 확인
                            assert response_data["sections_analyzed"] == len(FAKE_EVALUATION_CRITERIA)  # 분석 섹션 수 확인
                            assert response_data["contest_type"] == "예비창업패키지"  # contest_type 일치 확인

                            # 추가 검증: Pydantic 모델 인스턴스 생성 (테스트 목적, 실제 반환은 assert로 대체 가능)
                            AnalysisResponse(
                                report_json=response_data["report_json"],
                                sections_analyzed=response_data["sections_analyzed"],
                                contest_type=response_data["contest_type"]
                            )
