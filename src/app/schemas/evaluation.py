from pydantic import BaseModel, Field, Body
from typing import Optional, List, Dict, Any
from pydantic import validator
import json

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


class MarketInformation(BaseModel):
    # 시장 규모
    marker_size: Optional[float] = Field(None, description="시장 규모 (억원 단위)")
    #성장률
    growth_rate: Optional[float] = Field(None, description = "성장률 (%)")
    # 시장 트렌드
    market_trend: List[str] = Field(default_factory=list, description = "시장 트렌드 키워드")
    # 주요 경쟁사
    competitors: List[str] = Field(default_factory=list, description="주요 경쟁사")
    #타겟 고객 정보
    persona: Optional[Dict[str,Any]]= Field(None, description="타겟 고객 정보")
    #관련 규제 정보
    regulations: Optional[Dict[str,Any]] = Field(None, description="관련 규제 정보")
    #계절성 요인
    seasonal_factors: Optional[Dict[str,Any]]=Field(None,description="계절성 요인")

    @validator('marker_size')
    def market_size_must_be_positive(cls, value):
        if value is not None and value <= 0:
            raise ValueError('시장 규모는 0보다 커야 합니다.')
        return value

class RequestindustryData(BaseModel):
    # 시장 데이터 (JSONB 형식)
    market_data: MarketInformation = Field(..., description="시장 데이터")
    # 추가 메타데이터
    additional_data: Optional[Dict[str, Any]] = Field(None, description="추가 데이터 (자유 형식 JSONB)")
    # 검색 키워드
    keyword: Optional[str] = Field("marktet",description="검색 키워드")

    @validator('market_data')
    def validate_market_data(cls,v):
        if v.marker_size is not None and v.marker_size <= 0:
            raise ValueError('시장 규모는 0보다 커야 합니다.')
        if v.growth_rate is not None and  not (=100<=v.growth_rate<=1000):
            raise ValueError('성장률은 -100%에서 1000% 사이여야 합니다')
        return v

# 응답 모델 구조 정의
class ResponseindustryData(BaseModel):
    industry:str
    marketStatus: str
    expertOpinion: str
    processed_data: Optional[Dict[str,Any]] = None
