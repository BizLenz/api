# file: app/schemas/evaluation.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

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
