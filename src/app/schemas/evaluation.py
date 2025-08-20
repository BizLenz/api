from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
import json

# =====================================================
# 🔄 평가 기준 상수 정의 (예비창업패키지 기준)
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
    """사업계획서 평가 요청 (A안 단순구조 + 팀원 코드 호환)"""
    business_plan: str = Field(
        ...,
        description="평가할 사업계획서 내용",
        min_length=100  # 팀원과 상의 필요
    )
    additional_info: Optional[str] = Field(
        None,
        description="추가 정보 또는 특별 요청사항",
        max_length=500  # 팀원과 상의 필요
    )
    
    class Config:
        schema_extra = {
            "example": {
                "business_plan": "AI 기반 사업계획서 분석 서비스를 통해 창업자들이 보다 객관적이고 체계적인 사업계획서를 작성할 수 있도록 지원하는 서비스입니다...",
                "additional_info": "스타트업 대상 종합평가"
            }
        }

class SectionResult(BaseModel):
    """섹션별 결과 (UI 문서 기반)"""
    score: Optional[float] = Field(None, description="섹션 점수", ge=0, le=999.99)  # 🔄 DB 기준
    max_score: int = Field(..., description="섹션 최대 점수")
    analysis: Optional[str] = Field(None, description="Gemini 분석 내용")
    strengths: Optional[List[str]] = Field(default_factory=list, description="섹션별 강점")
    weaknesses: Optional[List[str]] = Field(default_factory=list, description="섹션별 약점")
    evidence_text: Optional[str] = Field(None, description="관련 내용 발췌/요약")
    
    @field_validator('score')
    @classmethod
    def score_in_range(cls, v, info):
        if v is not None and 'max_score' in info.data:
            max_score = info.data['max_score']
            if not (0 <= v <= max_score):
                raise ValueError(f'점수는 0과 {max_score} 사이여야 합니다.')
        return v

class CategoryResult(BaseModel):
    """카테고리별 결과 (예비창업패키지 최소기준 적용)"""
    score: Optional[float] = Field(None, description="카테고리 총점", ge=0, le=999.99)  # 🔄 DB 기준
    max_score: int = Field(..., description="카테고리 최대 점수")
    minimum_required: int = Field(..., description="최소 득점 기준")
    passed: Optional[bool] = Field(None, description="최소 기준 통과 여부")
    sections: List[str] = Field(..., description="포함된 섹션들")

class FileInfo(BaseModel):
    """파일 정보 (UI 문서 + DB BusinessPlan 테이블 연동)"""
    file_name: Optional[str] = Field(None, description="파일 이름")
    analysis_request_date: Optional[str] = Field(None, description="분석 요청일")
    evaluation_form: Optional[str] = Field("예비창업패키지", description="평가 양식")
    analysis_options: Optional[str] = Field(None, description="분석 옵션")

class KeywordAnalysis(BaseModel):
    """키워드 분석 (UI 문서 기반)"""
    keywords: List[str] = Field(default_factory=list, description="주요 키워드")
    frequencies: Optional[Dict[str, int]] = Field(None, description="키워드 빈도수")
    importance_scores: Optional[Dict[str, float]] = Field(None, description="중요도 점수")

class EvaluationResponse(BaseModel):
    """
    🔄 사업계획서 평가 응답 (analyses.evaluation_report JSONB에 통합 저장)
    DB 연동: 이 전체 객체가 analyses.evaluation_report에 JSON으로 저장됨
    """
    success: bool = Field(True, description="평가 성공 여부")
    error_message: Optional[str] = Field(None, description="에러 메시지")
    
    # 성공시에만 채워지는 필드들
    evaluation_id: Optional[str] = Field(None, description="평가 고유 ID (analyses.id)")
    total_score: Optional[float] = Field(None, description="총점", ge=0, le=999.99)  # 🔄 DB 기준
    
    # 파일 정보 (BusinessPlan 테이블 연동)
    file_info: Optional[FileInfo] = Field(None, description="파일 정보")
    
    # 🔄 섹션별 상세 결과 (예비창업패키지 7개 섹션)
    section_results: Optional[Dict[str, SectionResult]] = Field(
        None,
        description="섹션별 상세 점수 및 분석 (한국어 키 사용)"
    )
    
    # 🔄 카테고리별 결과 (예비창업패키지 4개 카테고리)
    category_results: Optional[Dict[str, CategoryResult]] = Field(
        None,
        description="카테고리별 점수 (문제인식, 해결방안, 성장전략, 팀구성)"
    )
    
    # 종합 분석 (AI 프롬프트 + UI 문서 기반)
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
    
    # 데이터 분석 결과 (UI 문서 기반)
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
    
    # 관련 데이터 (UI 문서 기반)
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
    
    # 🔄 탈락 위험도 (예비창업패키지 최소기준 기반)
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
# 🔄 시장 분석 관련 모델 (DB 연동 대응)
# =====================================================

class MarketInformation(BaseModel):
    """시장 정보 (DB MarketAnalysis 테이블과 연동)"""
    market_size: Optional[float] = Field(None, description="시장 규모 (억원 단위)")
    growth_rate: Optional[float] = Field(None, description="성장률 (%)")
    market_trend: List[str] = Field(default_factory=list, description="시장 트렌드 키워드")
    competitors: List[str] = Field(default_factory=list, description="주요 경쟁사")
    persona: Optional[Dict[str, Any]] = Field(None, description="타겟 고객 정보")
    regulations: Optional[Dict[str, Any]] = Field(None, description="관련 규제 정보")
    seasonal_factors: Optional[Dict[str, Any]] = Field(None, description="계절성 요인")

    @field_validator('market_size')
    @classmethod
    def market_size_must_be_positive(cls, value):
        if value is not None and value <= 0:
            raise ValueError('시장 규모는 0보다 커야 합니다.')
        return value

    @field_validator('growth_rate')
    @classmethod
    def growth_rate_range(cls, value):
        if value is not None and not (-100 <= value <= 1000):
            raise ValueError('성장률은 -100%에서 1000% 사이여야 합니다')
        return value

class RequestindustryData(BaseModel):
    """시장 분석 요청 (DB 시장분석 테이블들과 연동)"""
    market_data: MarketInformation = Field(..., description="시장 데이터")
    additional_data: Optional[Dict[str, Any]] = Field(
        None, 
        description="추가 데이터 (자유 형식 JSONB)"
    )
    keyword: Optional[str] = Field("market", description="검색 키워드")

class ResponseindustryData(BaseModel):
    """시장 분석 응답 (프론트엔드 기준 에러 처리)"""
    success: bool = Field(True, description="처리 성공 여부")  # 🔄 프론트엔드 기준
    error_message: Optional[str] = Field(None, description="에러 메시지")
    
    industry: Optional[str] = Field(None, description="산업 분류")
    market_status: Optional[str] = Field(None, description="시장 현황")
    expert_opinion: Optional[str] = Field(None, description="전문가 의견")
    processed_data: Optional[Dict[str, Any]] = Field(None, description="처리된 데이터")

# =====================================================
# 🔄 헬퍼 함수들 (예비창업패키지 기준)
# =====================================================

def get_section_max_score(section_name: str) -> int:
    """섹션명으로 최대 점수 반환 (UI 문서 참조)"""
    return SECTION_SCORES.get(section_name, 0)

def get_category_info(category_name: str) -> Dict[str, Any]:
    """카테고리명으로 정보 반환 (예비창업패키지 기준)"""
    return EVALUATION_CATEGORIES.get(category_name, {})

def get_all_sections() -> List[str]:
    """모든 평가 섹션 목록 반환 (팀원 코드 EVALUATION_CRITERIA 호환)"""
    return list(SECTION_SCORES.keys())

def calculate_category_score(section_scores: Dict[str, float], category_name: str) -> float:
    """카테고리별 총점 계산 (UI 문서 - 카테고리화 표시)"""
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
    """탈락 위험도 판정 (AI 프롬프트 + 에러처리 표 참조)"""
    minimum_checks = check_minimum_requirements(category_scores)
    return not all(minimum_checks.values())

def get_failed_categories(category_scores: Dict[str, float]) -> List[str]:
    """최소 기준 미달 카테고리 목록 (UI 문서 - 개선필요항목 모아보기)"""
    minimum_checks = check_minimum_requirements(category_scores)
    return [category for category, passed in minimum_checks.items() if not passed]

# =====================================================
# 🔄 DB 저장용 헬퍼 함수들 (analyses.evaluation_report JSONB 연동)
# =====================================================

def evaluation_response_to_db_json(response: EvaluationResponse) -> Dict[str, Any]:
    """EvaluationResponse를 analyses.evaluation_report JSONB 저장용 딕셔너리로 변환"""
    return response.model_dump(exclude_none=True)

def db_json_to_evaluation_response(db_json: Dict[str, Any]) -> EvaluationResponse:
    """analyses.evaluation_report JSONB에서 EvaluationResponse로 변환"""
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

# =====================================================
# 사용 예시 및 데이터 플로우 가이드
# =====================================================

"""
🔄 DB 연동 플로우:

1. 평가 요청 처리:
   request = EvaluationRequest(business_plan="...", additional_info="...")
   
2. Gemini 분석 수행:
   gemini_result = analyze_with_gemini(request.business_plan)
   
3. 응답 객체 생성:
   response = EvaluationResponse(
       success=True,
       total_score=85.5,
       section_results={
           "1.1. 창업아이템의 개발동기": SectionResult(score=12.5, max_score=15, ...),
           "1.2. 창업아이템의 목적(필요성)": SectionResult(score=13.0, max_score=15, ...)
       },
       category_results={
           "문제인식": CategoryResult(score=25.5, max_score=30, passed=True, ...)
       }
   )
   
4. DB 저장:
   analysis = Analysis(
       plan_id=business_plan.id,
       evaluation_report=evaluation_response_to_db_json(response),  # 🔄 JSONB에 통합 저장
       overall_score=response.total_score,
       status="완료",  # 🔄 한국어 상태값
       completed_at=datetime.now()
   )
   
5. DB 조회:
   analysis = session.query(Analysis).filter_by(id=analysis_id).first()
   response = db_json_to_evaluation_response(analysis.evaluation_report)
   
🔄 프론트엔드 연동:
- 파일 상태: "대기중", "분석중", "완료" (한국어)
- 카테고리명: "문제인식", "해결방안", "성장전략", "팀구성" (한국어)
- 섹션명: "1.1. 창업아이템의 개발동기" 등 (한국어, 점 포함)
- 점수 범위: 0.00-999.99 (DB Numeric(5,2) 기준)
"""