# file: app/schemas/evaluation.py
from __future__ import annotations
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, condecimal


class AnalysisCreateIn(BaseModel):
    contest_type: Literal["예비창업패키지"] = Field(default="예비창업패키지")
    file_path: str = Field(
        ..., description="이미 저장된 사업계획서 PDF의 S3 오브젝트 키"
    )
    analysis_model: str = Field(default="gemini-2.5-flash")
    json_model: str = Field(default="gemini-2.5-flash")
    timeout_sec: int = Field(default=120, ge=10, le=600)


class AnalysisResponse(BaseModel):
    report_json: str = Field(
        ..., description="Gemini가 생성한 최종 평가 보고서(JSON 문자열)"
    )
    sections_analyzed: int = Field(..., ge=0)
    contest_type: str = Field(...)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "report_json": '{"title": "예비창업패키지 사업계획서 최종 평가 보고서", ...}',
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
