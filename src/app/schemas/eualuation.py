from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- 모델 정의 ---

# EvaluationResponse에서 사용하기 위해 EvaluationRequest를 EvaluationSection으로 변경
class EvaluationSection(BaseModel):
    section_name: str = Field(
        ...,
        description="평가 섹션명"
    )
    max_score: int = Field(
        ...,
        description="섹션별 최대 배점",
        ge=1, le=100
    )
    questions: List[str] = Field(
        ...,
        description="해당 섹션의 평가 질문 목록",
        min_length=1  # min_items -> min_length 로 변경
    )

class EvaluationResponse(BaseModel):
    evaluation_type: str = Field(
        ...,
        description="평가 유형",
        examples=["comprehensive"]
    )
    sections: List[EvaluationSection] = Field(
        ...,
        description="평가할 섹션들의 목록",
        min_length=1 # min_items -> min_length 로 변경
    )
    business_plan: str = Field(
        ...,
        description="평가할 사업계획서 내용",
        min_length=10
    )
    additional_info: Optional[str] = Field(
        None,
        description="추가 정보 또는 특별 요청사항",
        max_length=500
    )
    
    # v2: Config 클래스 대신 model_config 딕셔너리 사용
    model_config = {
        "json_schema_extra": {
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
    }


class MarketInformation(BaseModel):
    market_size: Optional[float] = Field(None, description="시장 규모 (억원 단위)") # 오타 수정: marker_size -> market_size
    growth_rate: Optional[float] = Field(None, description="성장률 (%)")
    market_trend: List[str] = Field(default_factory=list, description="시장 트렌드 키워드")
    competitors: List[str] = Field(default_factory=list, description="주요 경쟁사")
    persona: Optional[Dict[str, Any]] = Field(None, description="타겟 고객 정보")
    regulations: Optional[Dict[str, Any]] = Field(None, description="관련 규제 정보")
    seasonal_factors: Optional[Dict[str, Any]] = Field(None, description="계절성 요인")

    # v2: @validator -> @field_validator 로 변경
    @field_validator('market_size')
    def market_size_must_be_positive(cls, value):
        if value is not None and value <= 0:
            raise ValueError('시장 규모는 0보다 커야 합니다.')
        return value
    
    # v2: growth_rate 유효성 검사를 해당 모델로 이동 및 수정
    @field_validator('growth_rate')
    def validate_growth_rate(cls, value):
        if value is not None and not (-100 <= value <= 1000):
            raise ValueError('성장률은 -100%에서 1000% 사이여야 합니다.')
        return value


class RequestindustryData(BaseModel):
    market_data: MarketInformation = Field(..., description="시장 데이터")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="추가 데이터 (자유 형식 JSONB)")
    keyword: Optional[str] = Field("market", description="검색 키워드")
    # v2: MarketInformation 모델에서 자체적으로 검증하므로 중복 validator 제거


class ResponseindustryData(BaseModel):
    industry: str
    marketStatus: str
    expertOpinion: str
    processed_data: Optional[Dict[str, Any]] = None


# --- FastAPI의 orm_mode 호환을 위한 추가 모델 예시 ---

class FileListResponse(BaseModel):
    id: int
    file_name: str
    file_size: int
    mime_type: str
    created_at: datetime

    # v2: orm_mode -> from_attributes 로 변경
    model_config = {
        "from_attributes": True
    }