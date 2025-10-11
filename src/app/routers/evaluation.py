# src/app/routers/evaluation.py
# S3 예외 처리 개선: '404'와 'NoSuchKey' 코드 체크 추가, 404 반환
# 이 파일은 사업계획서 분석 API 엔드포인트를 정의합니다.
# FastAPI 라우터를 사용하며, AWS S3에서 파일을 다운로드하고 Gemini AI로 분석합니다.
# JWT 인증은 Cognito Authorizer를 통해 처리되며, dependencies로 openid 스코프를 요구합니다.
# 수정: /request에서 분석 후 DB 저장을 통합하여 /record API를 불필요하게 함.

from __future__ import annotations
import asyncio
import pathlib
import tempfile
import boto3
import json  # report_json 파싱을 위한 라이브러리 (기본 내장)
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.evaluation import (
    AnalysisCreateIn,
    AnalysisResultOut,  # 반환 모델로 사용 (result_id 포함)
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

import google.generativeai as genai
from google.generativeai import types
from functools import partial
from app.models.models import AnalysisJob

router = APIRouter()
evaluation_router = APIRouter(dependencies=[Depends(require_scope("openid"))])

_s3 = boto3.client(
    "s3",
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
)

async def upload_file_async(path: str, display_name: str):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, partial(genai.upload_file, path=str(path), display_name=display_name)
    )

# 섹션 분석 함수: Gemini AI를 사용해 사업계획서 섹션을 분석
# uploaded_doc_file: Gemini에 업로드된 파일 객체
# criteria: 분석 기준 딕셔너리
async def _analyze_section(uploaded_doc_file: types.File, criteria: dict) -> dict:
    # 섹션별 프롬프트 구성 (pillars_description과 pillar_scoring_format 생성)
    # 이 부분은 사업계획서의 각 섹션을 평가 기준에 따라 분석 프롬프트를 만듭니다.
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

    # 프롬프트 템플릿 적용: 분석 기준을 바탕으로 Gemini에 전달할 프롬프트를 생성합니다.

    prompt = SECTION_ANALYSIS_PROMPT_TEMPLATE.format(
        section_name=criteria["section_name"],
        max_score=criteria["max_score"],
        pillars_description="\n    ".join(pillars_description),
        pillar_scoring_format="\n".join(pillar_scoring_format),
    )

    # Gemini 모델 초기화 및 콘텐츠 생성 (비동기 호출): settings에서 모델 이름을 불러와 사용합니다.
    model = genai.GenerativeModel(
        model_name=settings.gemini_model_analysis, system_instruction=SYSTEM_PROMPT
    )

    resp = await model.generate_content_async(
        contents=[prompt, uploaded_doc_file],
        generation_config=types.GenerationConfig(temperature=0.0),
    )

    # 응답 텍스트 추출 (실패 시 기본 텍스트 반환): AI 응답이 실패하면 기본 에러 메시지를 반환합니다.
    text = getattr(
        resp,
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
        # 1. 원본 JSON 문자열을 파이썬 딕셔너리로 로드합니다.
        llm_data = json.loads(report_json)

        # 2. 'score' 필드 추출: LLM 응답의 'total_score' 키를 사용합니다.
        #    .get()을 사용하여 키가 없더라도 오류 없이 None을 반환하도록 합니다.
        score = llm_data.get("total_score")

        # 3. 'summary' 필드 추출: LLM 응답의 'overall_assessment' 키를 사용합니다.
        summary = llm_data.get("overall_assessment", "") # 키가 없으면 빈 문자열을 반환

        # 4. 'details' 필드 구성: 원본 데이터에서 이미 추출한 정보를 제외한
        #    나머지 모든 상세 정보를 포함시킵니다.
        #    이렇게 하면 원본의 풍부한 정보를 잃지 않고 저장할 수 있습니다.
        details = dict(llm_data) # 원본 딕셔너리를 복사합니다.
        details.pop("total_score", None)        # 이미 사용한 키는 details에서 제거하여
        details.pop("overall_assessment", None) # 데이터 중복을 방지합니다.

        # 5. 최종적으로 변환된 딕셔너리를 반환합니다.
        return {
            "score": score,
            "summary": summary,
            "details": details
        }

    except (json.JSONDecodeError, AttributeError):
        # JSON 파싱에 실패하거나, 입력값이 문자열이 아닌 경우 등
        # 예외 상황에서는 빈 기본값을 반환하여 시스템 안정성을 확보합니다.
        return {
            "score": None,
            "summary": "",
            "details": {}
        }

# 분석 요청 엔드포인트: 사업계획서 PDF를 S3에서 다운로드하고 분석 후 DB에 저장
@evaluation_router.post(
    "/request",
    response_model=AnalysisResultOut,
    status_code=status.HTTP_201_CREATED,  # 반환 모델을 AnalysisResultOut으로 변경 (DB 저장 결과 포함)
)
async def create_analysis(
    req: AnalysisCreateIn, db: Session = Depends(get_db)
):  # DB 세션 추가: Depends(get_db)로 SQLAlchemy 세션을 주입합니다.
    try:
        new_job = AnalysisJob(
            plan_id=req.plan_id,  
            job_type=req.contest_type,
            status="processing",
        )
        db.add(new_job)
        db.flush()   
             
        # 임시 디렉토리 생성: 파일 다운로드 후 자동 삭제
        with tempfile.TemporaryDirectory() as td:
            # file_path 사용 부분 1: 파일명 추출 (S3 키의 마지막 부분을 파일명으로 사용)
            filename = req.file_path.split("/")[-1] or "input.pdf"
            local_path = pathlib.Path(td) / filename

            # file_path 사용 부분 2: S3에서 파일 다운로드 (req.file_path를 오브젝트 키로 사용)

            # file_path 사용 부분 2: S3에서 파일 다운로드 (req.file_path를 오브젝트 키로 사용)
            try:
                _s3.download_file(
                    settings.s3_bucket_name, req.file_path, str(local_path)
                )
            except ClientError as e:  # S3 클라이언트 에러 catch
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

            # Gemini 클라이언트 설정 및 파일 업로드: Google API 키를 settings에서 불러와 사용합니다.
            genai.configure(api_key=settings.google_api_key)
            uploaded_doc_file = genai.upload_file(
                path=str(local_path), display_name=filename
            )

            # 섹션 병렬 분석: asyncio.gather로 동시에 실행하여 효율성을 높입니다.
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
            report_json = getattr(final_resp, "text", "")

        # 수정된 부분: 분석 결과(report_json)를 파싱하여 DB에 저장
        # report_json을 딕셔너리로 변환 (파싱 실패 시 기본값 설정)
        try:
            report_data = transform_gemini_report(report_json)
            score = report_data["score"]  # report_json에 score 필드가 있다고 가정
            summary = report_data.get("summary", "")  # 요약 필드
            details = report_data.get("details", {})  # 상세 내용 (JSON으로 저장 가능)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="보고서 JSON 파싱 오류")

        # DB 저장: create_analysis_result 호출 (analysis_job_id는 요청에서 생성하거나 임시로 설정, 여기서는 예시로 'req.contest_type'을 사용)
        # 주의: 실제로 analysis_job_id는 유니크하게 생성해야 합니다. (예: UUID 사용 추천)
        saved_result = create_analysis_result(
            db,
            analysis_job_id=new_job.id,
            evaluation_type=req.contest_type,
            score=score if score is not None else None,
            summary=summary,
            details=details,  # details를 JSON 문자열로 저장(SQLAlchemy가 JSONB로 변환)
        )
        new_job.status = "completed"
        db.commit()
        db.refresh(saved_result)

    except asyncio.TimeoutError:
        db.rollback() 
        raise HTTPException(status_code=504, detail="분석 타임아웃")
    except HTTPException:
        db.rollback() 
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"분석 중 오류: {e}")

    # 저장된 결과 반환: AnalysisResultOut 모델로 반환 (result_id 포함)
    return saved_result


# 분석 결과 조회 엔드포인트: result_id로 조회 (기존 유지)
@evaluation_router.get(
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
