# file: app/schemas/evaluation.py
from __future__ import annotations
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, condecimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models import BusinessPlan, MarketAnalysis
from app.core.security import get_claims
from app.routers.files import get_current_user_id

analysis = APIRouter(prefix="/analysis", tags=["analysis"])

class AnalysisCreateIn(BaseModel):
    contest_type: Literal["예비창업패키지"] = Field(default="예비창업패키지")
    s3_key: str = Field(..., description="이미 저장된 사업계획서 PDF의 S3 오브젝트 키")
    analysis_model: str = Field(default="gemini-2.5-flash")
    json_model: str = Field(default="gemini-2.5-flash")
    timeout_sec: int = Field(default=120, ge=10, le=600)

class AnalysisResponse(BaseModel):
    report_json: str = Field(..., description="Gemini가 생성한 최종 평가 보고서(JSON 문자열)")
    sections_analyzed: int = Field(..., ge=0)
    contest_type: str = Field(...)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "report_json": "{\"title\": \"예비창업패키지 사업계획서 최종 평가 보고서\", ...}",
                    "sections_analyzed": 6,
                    "contest_type": "예비창업패키지",
                }
            ]
        }
    }

class AnalysisResultCreateIn(BaseModel):
    analysis_job_id: int = Field(..., description="연결할 분석 작업 ID")
    evaluation_type: Literal["overall", "market", "industry", "feedback"] = Field(
        ..., description="평가 유형"
    )
    score: Optional[condecimal(max_digits=5, decimal_places=2)] = Field(
        None, description="점수(0.00~100.00)"
    )
    summary: Optional[str] = Field(None, description="요약")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="분석 상세 JSON 데이터(JSONB로 저장)"
    )

    @field_validator("score")
    @classmethod
    def _check_score(cls, v):
        if v is None:
            return v
        if v < 0 or v > 100:
            raise ValueError("score must be between 0 and 100")
        return v

class AnalysisResultOut(BaseModel):
    id: int
    analysis_job_id: int
    evaluation_type: str
    score: Optional[condecimal(max_digits=5, decimal_places=2)] = None
    summary: Optional[str] = None
    details: Dict[str, Any]
    created_at: Optional[str] = None

    class Config:
        from_attributes = True  # ORM 객체 → Pydantic 변환 허용


#유저가 관련 업종/시장상황/전문적 의견 데이터 요청
@analysis.get("/industry-data", response_model=Dict[str, Any])
def get_industry_data(
    file_id: int = Query(..., description="사업계획서 파일 ID"),
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
):
    """
    특정 사업계획서(file_id)에 연결된 최신 industry-data 조회
    - 유저 본인의 파일만 접근 가능
    - 데이터 없으면 404 반환
    """
    user_id = get_current_user_id(claims)

    # 1. 파일 존재 여부 + 소유권 확인
    business_plan = (
        db.query(BusinessPlan)
        .filter(BusinessPlan.id == file_id, BusinessPlan.user_id == user_id)
        .first()
    )
    if not business_plan:
        raise HTTPException(status_code=404, detail="File not found or access denied")

    # 2. 최신 market_analysis 조회
    analysis_record = (
        db.query(MarketAnalysis)
        .filter(MarketAnalysis.plan_id == file_id)
        .order_by(desc(MarketAnalysis.created_at))
        .first()
    )
    if not analysis_record:
        raise HTTPException(status_code=404, detail="Market analysis not found")

    # 3. 응답 반환
    return {
        "status": "success",
        "data": {
            "industry_trends": analysis_record.industry_trends,
            "market_conditions": analysis_record.market_conditions,
        },
    }
