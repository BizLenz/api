# src/app/schemas/evaluation.py
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self
from typing import Optional, List, Dict, Any

# =====================================================
# 평가 기준 상수 정의 (예비창업패키지 기준)
# =====================================================

EVALUATION_CATEGORIES = {
    "문제인식": {
        "max_score": 30,
        "minimum_required": 18,
        "sections": ["1.1. 창업아이템의 개발동기", "1.2. 창업아이템의 목적(필요성)"]
    },
    "해결방안": {
        "max_score": 30,
        "minimum_required": 18,
        "sections": ["2.1. 창업아이템의 사업화 전략", "2.2. 시장분석 및 경쟁력 확보방안"]
    },
    "성장전략": {
        "max_score": 20,
        "minimum_required": 12,
        "sections": ["3.1. 자금소요 및 조달계획", "3.2. 시장진입 및 성과창출 전략"]
    },
    "팀구성": {
        "max_score": 20,
        "minimum_required": 12,
        "sections": ["4.1. 대표자 및 팀원의 보유역량"]
    }
}

SECTION_SCORES = {
    "1.1. 창업아이템의 개발동기": 15,
    "1.2. 창업아이템의 목적(필요성)": 15,
    "2.1. 창업아이템의 사업화 전략": 15,
    "2.2. 시장분석 및 경쟁력 확보방안": 15,
    "3.1. 자금소요 및 조달계획": 10,
    "3.2. 시장진입 및 성과창출 전략": 10,
    "4.1. 대표자 및 팀원의 보유역량": 20
}

# =====================================================
# 사업계획서 평가 관련 모델
# =====================================================

class EvaluationRequest(BaseModel):
    """사업계획서 평가 요청"""
    business_plan: str = Field(
        ...,
        description="평가할 사업계획서 내용",
        min_length=100
    )
    additional_info: Optional[str] = Field(
        None,
        description="추가 정보 또는 특별 요청사항",
        max_length=500
    )
    
    class Config:
        schema_extra = {
            "example": {
                "business_plan": "AI 기반 사업계획서 분석 서비스를 통해 창업자들이 보다 객관적이고 체계적인 사업계획서를 작성할 수 있도록 지원하는 서비스입니다...",
                "additional_info": "스타트업 대상 종합평가"
            }
        }

class SectionResult(BaseModel):
    """섹션별 결과"""
    score: Optional[float] = Field(None, description="섹션 점수", ge=0)
    max_score: int = Field(..., description="섹션 최대 점수")
    analysis: Optional[str] = Field(None, description="Gemini 분석 내용")
    strengths: Optional[List[str]] = Field(default_factory=list, description="섹션별 강점")
    weaknesses: Optional[List[str]] = Field(default_factory=list, description="섹션별 약점")
    evidence_text: Optional[str] = Field(None, description="관련 내용 발췌/요약")
    
    @model_validator(mode='after')
    def validate_score_range(self):
        if self.score is not None and self.score > self.max_score:
            raise ValueError(f'점수는 0과 {self.max_score} 사이여야 합니다.')
        return self

class CategoryResult(BaseModel):
    """카테고리별 결과 (예비창업패키지 최소기준 적용)"""
    score: Optional[float] = Field(None, description="카테고리 총점", ge=0)
    max_score: int = Field(..., description="카테고리 최대 점수")
    minimum_required: int = Field(..., description="최소 득점 기준")
    passed: Optional[bool] = Field(None, description="최소 기준 통과 여부")
    sections: List[str] = Field(..., description="포함된 섹션들")

class FileInfo(BaseModel):
    """파일 정보 (DB BusinessPlan 테이블 연동)"""
    file_name: Optional[str] = Field(None, description="파일 이름")
    analysis_request_date: Optional[str] = Field(None, description="분석 요청일")
    evaluation_form: Optional[str] = Field("예비창업패키지", description="평가 양식")
    analysis_options: Optional[str] = Field(None, description="분석 옵션")

class KeywordAnalysis(BaseModel):
    """키워드 분석"""
    keywords: List[str] = Field(default_factory=list, description="주요 키워드")
    frequencies: Optional[Dict[str, int]] = Field(None, description="키워드 빈도수")
    importance_scores: Optional[Dict[str, float]] = Field(None, description="중요도 점수")

class EvaluationResponse(BaseModel):
    """
    사업계획서 평가 응답 (analysis_results.details JSONB에 통합 저장)
    DB 연동: 이 전체 객체가 analysis_results.details에 JSON으로 저장됨
    """
    success: bool = Field(True, description="평가 성공 여부")
    error_message: Optional[str] = Field(None, description="에러 메시지")
    
    # 성공시에만 채워지는 필드들
    evaluation_id: Optional[str] = Field(None, description="평가 고유 ID")
    total_score: Optional[float] = Field(None, description="총점", ge=0, le=100)
    
    # 파일 정보 (BusinessPlan 테이블 연동)
    file_info: Optional[FileInfo] = Field(None, description="파일 정보")
    
    # 섹션별 상세 결과 (예비창업패키지 7개 섹션)
    section_results: Optional[Dict[str, SectionResult]] = Field(
        None,
        description="섹션별 상세 점수 및 분석 (한국어 키 사용)"
    )
    
    # 카테고리별 결과 (예비창업패키지 4개 카테고리)
    category_results: Optional[Dict[str, CategoryResult]] = Field(
        None,
        description="카테고리별 점수 (문제인식, 해결방안, 성장전략, 팀구성)"
    )
    
    # 종합 분석
    overall_strengths: Optional[List[str]] = Field(
        None,
        description="전체 사업계획서의 주요 강점 2-3개"
    )
    overall_weaknesses: Optional[List[str]] = Field(
        None,
        description="전체 사업계획서의 주요 약점 3-5개"
    )
    improvement_suggestions: Optional[List[str]] = Field(
        None,
        description="주요 개선 제안사항"
    )
    
    # 데이터 분석 결과
    keyword_analysis: Optional[KeywordAnalysis] = Field(
        None,
        description="키워드 분석 결과"
    )
    key_sentences: Optional[List[str]] = Field(
        None,
        description="핵심 문장/단락 추출"
    )
    tone_analysis: Optional[str] = Field(
        None,
        description="계획서 전반의 톤앤매너 분석"
    )
    
    # 관련 데이터 - JSONB에 자유롭게 저장
    data_sources: Optional[List[str]] = Field(
        None,
        description="데이터 분석 출처자료 URL"
    )
    related_indicators: Optional[Dict[str, Any]] = Field(
        None,
        description="관련 데이터 지표 (시장규모예측, 예상매출액 등)"
    )
    
    # Gemini 원본 응답
    gemini_full_analysis: Optional[str] = Field(
        None,
        description="Gemini 최종 분석 보고서 전문"
    )
    
    # 탈락 위험도 (예비창업패키지 최소기준 기반)
    risk_of_rejection: Optional[bool] = Field(
        None,
        description="탈락 위험도 (최소 기준 미달시 True)"
    )
    failed_categories: Optional[List[str]] = Field(
        default_factory=list,
        description="최소 기준 미달 카테고리 목록"
    )
    
    created_at: Optional[str] = Field(None, description="평가 생성 시간")

# =====================================================
# 헬퍼 함수들 (예비창업패키지 기준)
# =====================================================

def get_section_max_score(section_name: str) -> int:
    """섹션명으로 최대 점수 반환"""
    return SECTION_SCORES.get(section_name, 0)

def get_category_info(category_name: str) -> Dict[str, Any]:
    """카테고리명으로 정보 반환 (예비창업패키지 기준)"""
    return EVALUATION_CATEGORIES.get(category_name, {})

def get_all_sections() -> List[str]:
    """모든 평가 섹션 목록 반환"""
    return list(SECTION_SCORES.keys())

def calculate_category_score(section_scores: Dict[str, float], category_name: str) -> float:
    """카테고리별 총점 계산"""
    category_info = get_category_info(category_name)
    if not category_info:
        return 0.0
    
    total_score = 0.0
    for section_name in category_info["sections"]:
        if section_name in section_scores:
            total_score += section_scores[section_name]
    
    return total_score

def check_minimum_requirements(category_scores: Dict[str, float]) -> Dict[str, bool]:
    """각 카테고리별 최소 기준 통과 여부 확인 (예비창업패키지 최소 득점기준)"""
    results = {}
    for category_name, category_info in EVALUATION_CATEGORIES.items():
        if category_name in category_scores:
            score = category_scores[category_name]
            minimum = category_info["minimum_required"]
            results[category_name] = score >= minimum
        else:
            results[category_name] = False
    
    return results

def is_risk_of_rejection(category_scores: Dict[str, float]) -> bool:
    """탈락 위험도 판정"""
    minimum_checks = check_minimum_requirements(category_scores)
    return not all(minimum_checks.values())

def get_failed_categories(category_scores: Dict[str, float]) -> List[str]:
    """최소 기준 미달 카테고리 목록"""
    minimum_checks = check_minimum_requirements(category_scores)
    return [category for category, passed in minimum_checks.items() if not passed]

# =====================================================
# DB 저장용 헬퍼 함수들 (analysis_results.details JSONB 연동)
# =====================================================

def evaluation_response_to_db_json(response: EvaluationResponse) -> Dict[str, Any]:
    """EvaluationResponse를 analysis_results.details JSONB 저장용 딕셔너리로 변환"""
    return response.model_dump(exclude_none=True)

def db_json_to_evaluation_response(db_json: Dict[str, Any]) -> EvaluationResponse:
    """analysis_results.details JSONB에서 EvaluationResponse로 변환"""
    return EvaluationResponse(**db_json)

def create_file_info_from_business_plan(business_plan) -> FileInfo:
    """BusinessPlan 모델에서 FileInfo 생성"""
    return FileInfo(
        file_name=business_plan.file_name,
        analysis_request_date=business_plan.created_at.isoformat() if business_plan.created_at else None,
        evaluation_form="예비창업패키지",
        analysis_options="종합분석"
    )

def map_analysis_status_to_korean(status: str) -> str:
    """DB 영어 상태값을 프론트엔드 한국어 상태값으로 매핑"""
    status_map = {
        "pending": "대기중",
        "processing": "분석중", 
        "completed": "완료",
        "failed": "실패"
    }
    return status_map.get(status, status)

def map_korean_status_to_analysis(korean_status: str) -> str:
    """프론트엔드 한국어 상태값을 DB 영어 상태값으로 매핑"""
    reverse_map = {
        "대기중": "pending",
        "분석중": "processing",
        "완료": "completed", 
        "실패": "failed"
    }
    return reverse_map.get(korean_status, korean_status)