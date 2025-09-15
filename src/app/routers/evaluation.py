# file: app/routers/analysis.py
from __future__ import annotations

import asyncio
import pathlib
import tempfile
import boto3

from fastapi import APIRouter, HTTPException, status
from app.schemas.evaluation import AnalysisCreateIn, AnalysisResponse
from app.core.config import settings
from app.prompts.yeobi_startup import (
    SYSTEM_PROMPT,
    SECTION_ANALYSIS_PROMPT_TEMPLATE,
    FINAL_REPORT_PROMPT,
    EVALUATION_CRITERIA,
)

# Google GenAI SDK
from google import genai
from google.genai import types

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])

_s3 = boto3.client("s3", region_name=settings.aws_region)


async def _analyze_section(client: genai.Client, uploaded_doc, criteria: dict) -> dict:
    # 섹션별 프롬프트 구성 메서드
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

    resp = await client.models.generate_content_async(
        model=settings.gemini_model_analysis,
        contents=[prompt, uploaded_doc],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
        ),
    )
    text = getattr(resp, "text", "")
    if not text:
        text = f"### 분석 섹션: {criteria['section_name']}\n\n[ANALYSIS FAILED]\n\n---"
    return {"criteria": criteria, "analysis_text": text}


@router.post("/requests", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis(req: AnalysisCreateIn):
    # 1) S3에서 PDF 다운로드(별도의 파일 저장 API가 이미 업로드 완료했다고 가정)
    try:
        with tempfile.TemporaryDirectory() as td:
            filename = req.s3_key.split("/")[-1] or "input.pdf"
            local_path = pathlib.Path(td) / filename
            _s3.download_file(settings.s3_bucket, req.s3_key, str(local_path))

            # 2) Gemini 클라이언트 준비 및 파일 업로드
            client = genai.Client(api_key=settings.google_api_key)
            uploaded_doc = await client.files.upload_async(
                file=str(local_path),
                config={"mimeType": "application/pdf"},
            )

            # 3) 섹션 병렬 분석
            tasks = [_analyze_section(client, uploaded_doc, c) for c in EVALUATION_CRITERIA]
            try:
                results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=req.timeout_sec)
            except asyncio.TimeoutError:
                raise HTTPException(status_code=504, detail="분석 타임아웃")

            # 4) 최종 보고서 프롬프트 생성 및 호출
            structured_parts = []
            for r in results:
                c = r["criteria"]
                t = r["analysis_text"]
                structured_parts.append(
                    f"<item>\n"
                    f"<metadata>\n"
                    f"  section_name: {c['section_name']}\n"
                    f"  main_category: {c['main_category']}\n"
                    f"  category_max_score: {c['category_max_score']}\n"
                    f"  category_min_score: {c['category_min_score']}\n"
                    f"</metadata>\n"
                    f"<analysis>\n{t}\n</analysis>\n"
                    f"</item>"
                )
            structured_input = "\n\n".join(structured_parts)

            final_prompt = FINAL_REPORT_PROMPT.format(structured_analyses_input=structured_input)
            final_resp = await client.models.generate_content_async(
                model=req.json_model,
                contents=[final_prompt],
                config=types.GenerateContentConfig(
                    system_instruction="You are a system that generates JSON reports based on provided text.",
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )
            report_json = getattr(final_resp, "text", "{}")

    except _s3.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="S3 객체를 찾을 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류: {e}")

    # 5) 응답 반환
    return AnalysisResponse(
        report_json=report_json,
        sections_analyzed=len(EVALUATION_CRITERIA),
        contest_type=req.contest_type,
    )
