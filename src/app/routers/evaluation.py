from __future__ import annotations
import asyncio
import pathlib
import tempfile
import boto3
import json
from fastapi import APIRouter, HTTPException, status, Depends
from google.genai.types import UploadFileConfig, GenerateContentConfig, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.evaluation import (
    AnalysisCreateIn,
    AnalysisResultOut,
    AnalysisRequestAck,
)
from app.crud.evaluation import create_analysis_result, get_analysis_result
from app.core.config import settings
from app.core.security import require_scope
from app.prompts.pre_startup import (
    SYSTEM_PROMPT,
    SECTION_ANALYSIS_PROMPT_TEMPLATE,
    FINAL_REPORT_PROMPT,
    EVALUATION_CRITERIA,
)
from botocore.exceptions import ClientError

from google import genai

from functools import partial
from app.models.models import AnalysisJob

from typing import Dict, Any

router = APIRouter()
evaluation_router = APIRouter(dependencies=[Depends(require_scope("openid"))])

_s3 = boto3.client(
    "s3",
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
)


async def upload_file_async(client: genai.Client, path: str, display_name: str):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        partial(
            client.files.upload, path=str(path), config={display_name: display_name}
        ),
    )


async def _analyze_section(
    client: genai.Client, uploaded_doc_file: File, criteria: dict
) -> dict:
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

    prompt = SECTION_ANALYSIS_PROMPT_TEMPLATE.format(
        section_name=criteria["section_name"],
        max_score=criteria["max_score"],
        pillars_description="\n    ".join(pillars_description),
        pillar_scoring_format="\n".join(pillar_scoring_format),
    )

    response = client.models.generate_content(
        model=settings.gemini_model_analysis,
        contents=[prompt, uploaded_doc_file],
        config=GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
        ),
    )

    text = getattr(
        response,
        "text",
        f"### 분석 섹션: {criteria['section_name']}\n\n[ANALYSIS FAILED]\n\n---",
    )
    return {"criteria": criteria, "analysis_text": text}


def transform_gemini_report(report_json: str) -> Dict[str, Any]:
    """
    Gemini LLM이 생성한 상세 보고서 JSON 문자열을
    DB에 저장할 형식(score, summary, details)으로 변환합니다.

    Args:
        report_json (str): LLM으로부터 받은 원본 JSON 문자열

    Returns:
        Dict[str, Any]: {'score': ..., 'summary': ..., 'details': ...} 형태의 딕셔너리
    """
    try:
        llm_data = json.loads(report_json)

        score = llm_data.get("total_score")

        summary = llm_data.get("overall_assessment", "")

        details = dict(llm_data)
        details.pop("total_score", None)
        details.pop("overall_assessment", None)

        return {"score": score, "summary": summary, "details": details}

    except (json.JSONDecodeError, AttributeError):
        return {"score": None, "summary": "", "details": {}}


@evaluation_router.post(
    "/request",
    response_model=AnalysisRequestAck,
    status_code=status.HTTP_202_ACCEPTED,
    summary="사업계획서 분석 요청 및 저장",
    description="S3에 저장된 사업계획서 PDF를 다운로드하여 Gemini AI로 분석을 수행하고, 결과를 DB에 저장합니다. 동기적으로 처리되며, 완료 후 확인 메시지를 반환합니다.",
)
async def create_analysis(req: AnalysisCreateIn, db: Session = Depends(get_db)):
    try:
        new_job = AnalysisJob(
            plan_id=req.plan_id,
            job_type=req.contest_type,
            status="processing",
        )
        db.add(new_job)
        db.flush()

        with tempfile.TemporaryDirectory() as td:
            filename = req.file_path.split("/")[-1] or "input.pdf"
            local_path = pathlib.Path(td) / filename

            try:
                _s3.download_file(
                    settings.s3_bucket_name, req.file_path, str(local_path)
                )
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code in ["404", "NoSuchKey"]:
                    raise HTTPException(
                        status_code=404, detail="S3 객체를 찾을 수 없습니다."
                    )
                elif error_code == "403":
                    raise HTTPException(
                        status_code=403, detail="S3 접근 권한이 없습니다."
                    )
                else:
                    raise HTTPException(
                        status_code=500, detail=f"S3 다운로드 오류: {error_code} - {e}"
                    )

            client = genai.Client(api_key=settings.google_api_key)
            uploaded_doc_file = client.files.upload(
                file=str(local_path), config=UploadFileConfig(display_name=filename)
            )

            tasks = [
                _analyze_section(client, uploaded_doc_file, c)
                for c in EVALUATION_CRITERIA
            ]
            results = await asyncio.wait_for(
                asyncio.gather(*tasks), timeout=req.timeout_sec
            )

            structured_parts = [
                f"<item>\n<metadata>\n  section_name: {r['criteria']['section_name']}\n  main_category: {r['criteria']['main_category']}\n  category_max_score: {r['criteria']['category_max_score']}\n  category_min_score: {r['criteria']['category_min_score']}\n</metadata>\n<analysis>\n{r['analysis_text']}\n</analysis>\n</item>"
                for r in results
            ]
            final_prompt = FINAL_REPORT_PROMPT.format(
                structured_analyses_input="\n\n".join(structured_parts)
            )

            response = client.models.generate_content(
                model=req.json_model,
                contents=[final_prompt],
                config=GenerateContentConfig(
                    system_instruction="You are a system that generates JSON reports based on provided text.",
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )

            report_json = getattr(response, "text", "")

        try:
            report_data = transform_gemini_report(report_json)
            score = report_data["score"]
            summary = report_data.get("summary", "")
            details = report_data.get("details", {})
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="보고서 JSON 파싱 오류")

        create_analysis_result(
            db,
            analysis_job_id=new_job.id,
            evaluation_type=req.contest_type,
            score=score if score is not None else None,
            summary=summary,
            details=details,
        )
        new_job.status = "completed"
        db.commit()
        db.refresh(new_job)

    except asyncio.TimeoutError:
        db.rollback()
        raise HTTPException(status_code=504, detail="분석 타임아웃")
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"분석 중 오류: {e}")

    return {
        "message": "분석 요청이 성공적으로 처리되었습니다.",
        "analysis_job_id": new_job.id,
        "status": new_job.status,
    }


@evaluation_router.get(
    "/results/{plan_id}",
    response_model=AnalysisResultOut,
    summary="Get analysis result for a specific plan_id",
    description="Get the analysis result for a specific plan_id",
)
def get_result_endpoint(plan_id: int, db: Session = Depends(get_db)):
    obj = get_analysis_result(db, plan_id=plan_id)
    if not obj:
        raise HTTPException(status_code=404, detail="analysis result not found")
    return obj
