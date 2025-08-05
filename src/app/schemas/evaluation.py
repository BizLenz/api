from pydantic import BaseModel, Field, Body
from typing import Optional, List 
import requests

class EvaluationRequest(BaseModel):
   section_name: str = Field(
    ...,
    description = "평가 섹션명"
   )
   max_score: int = Field(
    ...,
    description = "섹션별 최대 배점",
    ge =1, le=100
   )
   questions: List[str] = Field(
    ...,
    description = "해당 섹션의 평가 질문 목록"
    min_items=1
   )

class EvaluationResponse(BaseModel):
    evaluation_type: str =Field(
        ...,
        description = "평가 유형",
        examples=["comprehensive"]
    )
    sections: List[EvaluationSection]=Field(
        ...,
        description="평가할 섹션들의 목록",
        min_items=1 # 최소 섹션 필요
    )
    business_plan: str =Field(
        ...,
        description="평가할 사업계획서 내용",
        min_length=10 # 최소 길이 제한
    )
    additional_info:Optional[str]=Field(
        None,
        description="추가 정보 또는 특별 요청사항",
        max_length=500
    )
    
    class Config:
        schema_extra = {
            "example": {
                "evaluation_type": "comprehensive",
                "sections": [
                    {
                        "section_name": "3.2. 시장진입 및 성과창출 전략",
                        "max_score": 10,
                        "questions": [
                            "수익모델별 예상 매출 비중은 어떻게 되는가?",
                            "주요 수익모델의 가격정책은 어떻게 구성되어 있는가?"
                        ]
                    }
                ],
                "business_plan": "AI 기반 사업계획서 분석 서비스...",
                "additional_info": "스타트업 대상 종합평가"
            }
        }

class RequestData(BaseModel):
    result: str =Field(..., description="전체 분석 결과")
    sections_evaluated: List[str] = Field(..., description = "평가된 섹션 목록")
    total_max_score: int = Field(..., description="전체 최대 점수")
    evaluation_type: str = Field(..., description="수행된 평가 유형")

    class Config:
        schema_extra{
            "example": {
                "result": "종합 평가 결과: 우수한 시장 분석과 전략이 돋보입니다...",
                "sections_evaluated": ["3.2. 시장진입 및 성과창출 전략"],
                "total_max_score": 10,
                "evaluation_type": "comprehensive"
            }
        }
