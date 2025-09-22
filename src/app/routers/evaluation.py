# src/app/routers/evaluation.py
# S3 예외 처리 개선: '404'와 'NoSuchKey' 코드 체크 추가, 404 반환
# 이 파일은 사업계획서 분석 API 엔드포인트를 정의합니다.
# FastAPI 라우터를 사용하며, AWS S3에서 파일을 다운로드하고 Gemini AI로 분석합니다.
# JWT 인증은 Cognito Authorizer를 통해 처리되며, dependencies로 openid 스코프를 요구합니다.

from __future__ import annotations
import asyncio
import pathlib
import tempfile
import boto3
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.evaluation import (
    AnalysisCreateIn,
    AnalysisResponse,
    AnalysisResultCreateIn,
    AnalysisResultOut,
)
from app.crud.evaluation import create_analysis_result, get_analysis_result
from app.core.config import settings
from app.prompts.yeobi_startup import (
    SYSTEM_PROMPT,
    SECTION_ANALYSIS_PROMPT_TEMPLATE,
    FINAL_REPORT_PROMPT,
    EVALUATION_CRITERIA,
)
from botocore.exceptions import ClientError

# Google GenAI SDK (최신 방식 Import)
import google.generativeai as genai
from google.generativeai import types

# FastAPI 라우터 정의: openid 스코프를 요구하여 인증된 사용자만 접근 가능
router = APIRouter(dependencies=[Depends(require_scope("openid"))])

# AWS S3 클라이언트 초기화: settings에서 region과 bucket 이름을 불러옴
_s3 = boto3.client("s3", region_name=settings.aws_region)

# 섹션 분석 함수: Gemini AI를 사용해 사업계획서 섹션을 분석
# uploaded_doc_file: Gemini에 업로드된 파일 객체
# criteria: 분석 기준 딕셔너리
async def _analyze_section(uploaded_doc_file: types.File, criteria: dict) -> dict:
    # 섹션별 프롬프트 구성 (pillars_description과 pillar_scoring_format 생성)
    pillars_description = []
    pillar_scoring_format = []
    for pillar_name, pillar_data in criteria["pillars"].items():
        questions_str = "\n".join(
            [f"  - {q}" for q in pillar_data.get("questions", [])]
        )
        pillars_description.append(
            f"- **{pillar_name}:** {pillar_data['description']}\n"
            f"  **[세부 검토사항]**\n{questions_str}"
        )
        pillar_scoring_format.append(
            f"- **{pillar_name}:**\n"
            f"  - **분석:** [사업계획서의 관련 내용을 여기에 분석/요약]\n"
            f"  - **점수:** [루브릭에 따른 점수] / {pillar_name.split('(')[-1].replace('점)', '').strip()}점\n"
            f"  - **근거:** [점수 부여에 대한 구체적인 이유]"
        )

    # 프롬프트 템플릿 적용
    prompt = SECTION_ANALYSIS_PROMPT_TEMPLATE.format(
        section_name=criteria["section_name"],
        max_score=criteria["max_score"],
        pillars_description="\n    ".join(pillars_description),
        pillar_scoring_format="\n".join(pillar_scoring_format),
    )

    # Gemini 모델 초기화 및 콘텐츠 생성 (비동기 호출)
    model = genai.GenerativeModel(
        model_name=settings.gemini_model_analysis, system_instruction=SYSTEM_PROMPT
    )

    resp = await model.generate_content_async(
        contents=[prompt, uploaded_doc_file],
        generation_config=types.GenerationConfig(temperature=0.0),
    )

    # 응답 텍스트 추출 (실패 시 기본 텍스트 반환)
    text = getattr(
        resp,
        "text",
        f"### 분석 섹션: {criteria['section_name']}\n\n[ANALYSIS FAILED]\n\n---",
    )
    return {"criteria": criteria, "analysis_text": text}

# 분석 요청 엔드포인트: 사업계획서 PDF를 S3에서 다운로드하고 분석
@router.post(
    "/request", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED
)
async def create_analysis(req: AnalysisCreateIn):
    try:
        # 임시 디렉토리 생성: 파일 다운로드 후 자동 삭제
        with tempfile.TemporaryDirectory() as td:
            # file_path 사용 부분 1: 파일명 추출 (S3 키의 마지막 부분을 파일명으로 사용)
            filename = req.file_path.split("/")[-1] or "input.pdf"
            local_path = pathlib.Path(td) / filename

            # file_path 사용 부분 2: S3에서 파일 다운로드 (req.file_path를 오브젝트 키로 사용)
            try:
                _s3.download_file(settings.s3_bucket_name, req.file_path, str(local_path))
            except ClientError as e:  # S3 클라이언트 에러 catch
                error_code = e.response["Error"]["Code"]
                if error_code in ["404", "NoSuchKey"]:  # 파일 없음 에러 처리
                    raise HTTPException(
                        status_code=404, detail="S3 객체를 찾을 수 없습니다."
                    )
                # 다른 에러(예: 권한 문제)에 대한 핸들링 추가 (추천: 로그 기록)
                raise HTTPException(status_code=500, detail=f"S3 다운로드 오류: {error_code} - {e}")

            # Gemini 클라이언트 설정 및 파일 업로드
            genai.configure(api_key=settings.google_api_key)
            uploaded_doc_file = await genai.upload_file_async(
                path=str(local_path), display_name=filename
            )

            # 섹션 병렬 분석: asyncio.gather로 동시에 실행
            tasks = [
                _analyze_section(uploaded_doc_file, c) for c in EVALUATION_CRITERIA
            ]
            results = await asyncio.wait_for(
                asyncio.gather(*tasks), timeout=req.timeout_sec
            )

            # 최종 보고서 프롬프트 생성 및 JSON 보고서 생성
            structured_parts = [
                f"<item>\n<metadata>\n  section_name: {r['criteria']['section_name']}\n  main_category: {r['criteria']['main_category']}\n  category_max_score: {r['criteria']['category_max_score']}\n  category_min_score: {r['criteria']['category_min_score']}\n</metadata>\n<analysis>\n{r['analysis_text']}\n</analysis>\n</item>"
                for r in results
            ]
            final_prompt = FINAL_REPORT_PROMPT.format(
                structured_analyses_input="\n\n".join(structured_parts)
            )

            final_report_model = genai.GenerativeModel(
                model_name=req.json_model,
                system_instruction="You are a system that generates JSON reports based on provided text.",
            )
            final_resp = await final_report_model.generate_content_async(
                contents=[final_prompt],
                generation_config=types.GenerationConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )
            report_json = getattr(final_resp, "text", "{}")

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="분석 타임아웃")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"분석 중 오류: {e}")

    # 분석 응답 반환
    return AnalysisResponse(
        report_json=report_json,
        sections_analyzed=len(EVALUATION_CRITERIA),
        contest_type=req.contest_type,
    )

# --- 아래의 DB 관련 엔드포인트들은 그대로 유지합니다 ---
# 분석 결과 기록 엔드포인트: DB에 결과 저장
@router.post(
    "/record",
    response_model=AnalysisResultOut,
    status_code=status.HTTP_201_CREATED,
    summary="분석 결과 기록",
    description="분석 결과를 DB에 기록합니다.",
)
def create_result_endpoint(
    payload: AnalysisResultCreateIn, db: Session = Depends(get_db)
):
    try:
        obj = create_analysis_result(
            db,
            analysis_job_id=payload.analysis_job_id,
            evaluation_type=payload.evaluation_type,
            score=float(payload.score) if payload.score is not None else None,
            summary=payload.summary,
            details=payload.details,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB 기록 중 오류: {e}")
    return obj

# 분석 결과 조회 엔드포인트: result_id로 조회
@router.get(
    "/results/{result_id}",
    response_model=AnalysisResultOut,
    summary="분석 결과 단건 조회",
    description="기본 키(result_id)로 저장된 분석 결과 레코드를 조회(SELECT)합니다.",
)
def get_result_endpoint(result_id: int, db: Session = Depends(get_db)):
    obj = get_analysis_result(db, result_id=result_id)
    if not obj:
        raise HTTPException(status_code=404, detail="analysis result not found")
    return obj
