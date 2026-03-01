from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import tempfile
from typing import Dict, Any

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from google import genai
from google.genai.types import File, GenerateContentConfig, UploadFileConfig
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import PlanStatus
from app.core.security import require_scope
from app.crud.evaluation import create_analysis_result, get_analysis_result
from app.database import get_db
from app.models.models import AnalysisJob
from app.prompts.example.pre_startup import (
    EVALUATION_CRITERIA,
    FINAL_REPORT_PROMPT,
    SECTION_ANALYSIS_PROMPT_TEMPLATE,
    SYSTEM_PROMPT,
)
from app.schemas.evaluation import (
    AnalysisCreateIn,
    AnalysisRequestAck,
    AnalysisResultOut,
)
from app.services.s3_service import make_boto3_client

logger = logging.getLogger(__name__)

router = APIRouter()
evaluation_router = APIRouter(dependencies=[Depends(require_scope("openid"))])


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
            f"  **[Detailed Review Items]**\n{questions_str}"
        )
        pillar_scoring_format.append(
            f"- **{pillar_name}:**\n"
            f"  - **Analysis:** [Analyze/summarize relevant content from the business plan here]\n"
            # defined in the gitignored prompts file; update if pillar names are translated
            f"  - **Score:** [Score per rubric] / {pillar_name.split('(')[-1].replace('점)', '').strip()}pts\n"
            f"  - **Justification:** [Specific reason for the given score]"
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
        f"### Analysis Section: {criteria['section_name']}\n\n[ANALYSIS FAILED]\n\n---",
    )
    return {"criteria": criteria, "analysis_text": text}


def transform_gemini_report(report_json: str) -> Dict[str, Any]:
    """Transform raw Gemini JSON report into DB-storable format"""
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
    summary="Request business plan analysis",
    description="Download business plan from storage, analyse with Gemini AI, and persist results.",
)
async def create_analysis(req: AnalysisCreateIn, db: Session = Depends(get_db)):
    try:
        new_job = AnalysisJob(
            plan_id=req.plan_id,
            job_type=req.contest_type,
            status=PlanStatus.PROCESSING,
        )
        db.add(new_job)
        db.flush()

        with tempfile.TemporaryDirectory() as td:
            filename = req.file_path.split("/")[-1] or "input.pdf"
            local_path = pathlib.Path(td) / filename

            storage_client = make_boto3_client()
            try:
                storage_client.download_file(
                    settings.storage_bucket_name, req.file_path, str(local_path)
                )
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code in ["404", "NoSuchKey"]:
                    raise HTTPException(
                        status_code=404, detail="File not found in storage."
                    )
                elif error_code == "403":
                    raise HTTPException(
                        status_code=403, detail="Storage access denied."
                    )
                else:
                    raise HTTPException(
                        status_code=500, detail=f"Storage error: {error_code}"
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
                f"<item>\n<metadata>\n  section_name: {r['criteria']['section_name']}\n"
                f"  main_category: {r['criteria']['main_category']}\n"
                f"  category_max_score: {r['criteria']['category_max_score']}\n"
                f"  category_min_score: {r['criteria']['category_min_score']}\n"
                f"</metadata>\n<analysis>\n{r['analysis_text']}\n</analysis>\n</item>"
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

        report_data = transform_gemini_report(report_json)
        create_analysis_result(
            db,
            analysis_job_id=new_job.id,
            evaluation_type=req.contest_type,
            score=report_data["score"],
            summary=report_data.get("summary", ""),
            details=report_data.get("details", {}),
        )
        new_job.status = PlanStatus.COMPLETED

        from app.models.models import BusinessPlan

        plan = db.query(BusinessPlan).filter(BusinessPlan.id == req.plan_id).first()
        if plan:
            plan.latest_job_id = new_job.id

        db.commit()
        db.refresh(new_job)

    except asyncio.TimeoutError:
        db.rollback()
        raise HTTPException(status_code=504, detail="Analysis timed out")
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Analysis failed for plan %s", req.plan_id)
        raise HTTPException(
            status_code=500, detail="Analysis failed. Please try again."
        )

    return {
        "message": "Analysis completed successfully.",
        "analysis_job_id": new_job.id,
        "status": new_job.status,
    }


@evaluation_router.get(
    "/results/{plan_id}",
    response_model=AnalysisResultOut,
    summary="Get analysis result for a plan",
)
def get_result_endpoint(plan_id: int, db: Session = Depends(get_db)):
    obj = get_analysis_result(db, plan_id=plan_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    return obj
