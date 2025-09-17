# src/app/routers/analysis.py

from __future__ import annotations
import asyncio
import pathlib
import tempfile
import boto3
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.evaluation import AnalysisCreateIn, AnalysisResponse, AnalysisResultCreateIn, AnalysisResultOut
from app.crud.evaluation import create_analysis_result, get_analysis_result
from app.core.config import settings
from app.prompts.yeobi_startup import (
    SYSTEM_PROMPT,
    SECTION_ANALYSIS_PROMPT_TEMPLATE,
    FINAL_REPORT_PROMPT,
    EVALUATION_CRITERIA,
)

# Google GenAI SDK (최신 방식 Import)
import google.generativeai as genai
from google.generativeai import types

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])

_s3 = boto3.client("s3", region_name=settings.aws_region)


# 첫 번째 인자를 client가 아닌 uploaded_doc_file로 받도록 변경하고 타입 힌트를 명확히 합니다.
async def _analyze_section(uploaded_doc_file: types.File, criteria: dict) -> dict:
    # 섹션별 프롬프트 구성
    pillars_description = []
    pillar_scoring_format = []
    for pillar_name, pillar_data in criteria["pillars"].items():
        questions_str = "\n".join([f"  - {q}" for q in pillar_data.get("questions", [])])
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

    prompt = SECTION_ANALYSIS_PROMPT_TEMPLATE.format(
        section_name=criteria["section_name"],
        max_score=criteria["max_score"],
        pillars_description="\n    ".join(pillars_description),
        pillar_scoring_format="\n".join(pillar_scoring_format),
    )

    # 최신 API 호출 방식
    model = genai.GenerativeModel(
        model_name=settings.gemini_model_analysis,
        system_instruction=SYSTEM_PROMPT
    )
    
    resp = await model.generate_content_async(
        contents=[prompt, uploaded_doc_file],
        generation_config=types.GenerationConfig(temperature=0.0),
    )
    
    text = getattr(resp, "text", f"### 분석 섹션: {criteria['section_name']}\n\n[ANALYSIS FAILED]\n\n---")
    return {"criteria": criteria, "analysis_text": text}


@router.post("/request", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis(req: AnalysisCreateIn):
    try:
        with tempfile.TemporaryDirectory() as td:
            filename = req.s3_key.split("/")[-1] or "input.pdf"
            local_path = pathlib.Path(td) / filename
            _s3.download_file(settings.s3_bucket, req.s3_key, str(local_path))

            # Gemini 클라이언트 준비 및 파일 업로드 (최신 방식)
            genai.configure(api_key=settings.google_api_key)
            uploaded_doc_file = await genai.upload_file_async(
                path=str(local_path),
                display_name=filename
            )

            # 섹션 병렬 분석 (이제 호출 방식과 함수 정의가 일치합니다)
            tasks = [_analyze_section(uploaded_doc_file, c) for c in EVALUATION_CRITERIA]
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=req.timeout_sec)

            # 최종 보고서 프롬프트 생성 및 호출
            structured_parts = [
                f"<item>\n<metadata>\n  section_name: {r['criteria']['section_name']}\n  main_category: {r['criteria']['main_category']}\n  category_max_score: {r['criteria']['category_max_score']}\n  category_min_score: {r['criteria']['category_min_score']}\n</metadata>\n<analysis>\n{r['analysis_text']}\n</analysis>\n</item>"
                for r in results
            ]
            final_prompt = FINAL_REPORT_PROMPT.format(structured_analyses_input="\n\n".join(structured_parts))

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

    except _s3.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="S3 객체를 찾을 수 없습니다.")
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="분석 타임아웃")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류: {e}")

    return AnalysisResponse(
        report_json=report_json,
        sections_analyzed=len(EVALUATION_CRITERIA),
        contest_type=req.contest_type,
    )

# --- 아래의 DB 관련 엔드포인트들은 그대로 유지합니다 ---
@router.post(
    "/record",
    response_model=AnalysisResultOut,
    status_code=status.HTTP_201_CREATED,
    summary="분석 결과 기록",
    description="분석 결과를 DB에 기록합니다.",
)
def create_result_endpoint(payload: AnalysisResultCreateIn, db: Session = Depends(get_db)):
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
