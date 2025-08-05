from pydantic import BaseModel, Field
from typing import Optional, List 

class EvaluationRequest(BaseModel):
   """
   사업계획서 평가 요청 데이터 모델
   클라이언트가 보내는 입력을 검증함.
   """
   evaluation_type: str = Field(
        ...,
        description="평가 유형 (예: 'business_plan')",
        example="business_plan"
   )
   evlauation_criteria: Optional[List[str]] = Field(
        None,
        description="평가 기준 목록",
        example=["시장성", "재무 계획", "팀 구성"]
   )
   additional_info: Optional[str] = Field(
        None,   
        description="추가 정보 (예: 사업 계획서 요약)",
        max_length=500
   )

    class Config:
        schema_extra = {
            "example": {
                "evaluation_type": "business_plan",
                "evaluation_criteria": ["시장성", "재무 계획", "팀 구성"],
                "additional_info": "이 사업은 혁신적인 기술을 기반으로 합니다."
            }
        }

class EvaluationResponse(BaseModel):
    """
    사업계획서 평가 응답 데이터 모델
    서버가 클라이언트에 보내는 응답을 정의함.
    """
    result: str = Field(
        ...,
        description="평가 결과 (예: '합격', '불합격')",  
        example="합격"
    )
    score: Optional[int] = Field(
        None,
        description = "전체 평가 점수(0-100)",
        ge=0, le=100,
        example = [["재무 예측을 더 구체적으로 하세요.", "위험 분석을 추가하세요."]]
    )
    suggestions: Optional[List[str]] = Field(
        None,
        description = "추가 개선 사항 목록",
        example=["재무 예측을 더 구체적으로 하세요.", "위험 분석을 추가하세요."]
    )
    error: Optional[str] = Field(
        None,
        description = "에러 발생 메시지"
    )
    class Config:
        schema_extra = {
            "example": {
                "result": "합격",
                "score": 85,
                "suggestions": ["재무 예측을 더 구체적으로 하세요.", "위험 분석을 추가하세요."],
                "error": None
            }
        }