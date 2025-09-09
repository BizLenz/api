# src/app/schemas/evaluation.py
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self
from typing import Optional, List, Dict, Any
from decimal import Decimal

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
    """섹션별 결과 (archive.py 출력 기반)"""
    score: Optional[Decimal] = Field(None, description="섹션 점수", ge=0, le=999.99)
    max_score: int = Field(..., description="섹션 최대 점수")
    analysis: Optional[str] = Field(None, description="Gemini 분석 내용", max_length=10000)
    
    @model_validator(mode='after')
    def validate_score_range(self) -> Self:
        if self.score is not None:
            if self.score < 0:
                raise ValueError('점수는 0 이상이어야 합니다.')
            if self.score > self.max_score:
                raise ValueError(f'점수는 {self.max_score} 이하여야 합니다.')
            if self.score.as_tuple().exponent < -2:
                raise ValueError('점수는 소수점 2자리까지만 허용됩니다.')
        return self

class CategoryResult(BaseModel):
    """카테고리별 결과 (예비창업패키지 최소기준 적용)"""
    score: Optional[Decimal] = Field(None, description="카테고리 총점", ge=0, le=999.99)
    max_score: int = Field(..., description="카테고리 최대 점수")
    minimum_required: int = Field(..., description="최소 득점 기준")
    passed: Optional[bool] = Field(None, description="최소 기준 통과 여부")
    sections: List[str] = Field(..., description="포함된 섹션들")
    
    @model_validator(mode='after')
    def validate_score_and_set_passed(self) -> Self:
        if self.score is not None:
            if self.score < 0:
                raise ValueError('카테고리 점수는 0 이상이어야 합니다.')
            if self.score > self.max_score:
                raise ValueError(f'카테고리 점수는 {self.max_score} 이하여야 합니다.')
            self.passed = self.score >= self.minimum_required
        return self

class FileInfo(BaseModel):
    """파일 정보 (DB BusinessPlan 테이블 연동)"""
    file_name: Optional[str] = Field(None, description="파일 이름", max_length=255)
    analysis_request_date: Optional[str] = Field(None, description="분석 요청일")
    evaluation_form: Optional[str] = Field("예비창업패키지", description="평가 양식", max_length=50)
    analysis_options: Optional[str] = Field(None, description="분석 옵션", max_length=100)

class EvaluationResponse(BaseModel):
    """
    사업계획서 평가 응답 (archive.py 출력 구조 기반)
    DB 연동: 이 전체 객체가 analysis_results.details에 JSON으로 저장됨
    """
    success: bool = Field(True, description="평가 성공 여부")
    error_message: Optional[str] = Field(None, description="에러 메시지", max_length=1000)
    
    # 성공시에만 채워지는 필드들
    evaluation_id: Optional[str] = Field(None, description="평가 고유 ID", max_length=50)
    total_score: Optional[Decimal] = Field(None, description="총점", ge=0, le=100)
    
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
    
    # 종합 분석 (archive.py 출력에서 추출되는 내용)
    overall_strengths: Optional[List[str]] = Field(
        None,
        description="전체 사업계획서의 주요 강점",
        max_items=5
    )
    overall_weaknesses: Optional[List[str]] = Field(
        None,
        description="전체 사업계획서의 주요 약점",
        max_items=10
    )
    improvement_suggestions: Optional[List[str]] = Field(
        None,
        description="주요 개선 제안사항",
        max_items=15
    )
    
    # Gemini 원본 응답 (archive.py에서 생성되는 전체 텍스트)
    gemini_full_analysis: Optional[str] = Field(
        None,
        description="Gemini 최종 분석 보고서 전문",
        max_length=50000
    )
    
    # 탈락 위험도 (예비창업패키지 최소기준 기반)
    risk_of_rejection: Optional[bool] = Field(
        None,
        description="탈락 위험도 (최소 기준 미달시 True)"
    )
    failed_categories: Optional[List[str]] = Field(
        default_factory=list,
        description="최소 기준 미달 카테고리 목록",
        max_items=4
    )
    
    created_at: Optional[str] = Field(None, description="평가 생성 시간")
    
    @model_validator(mode='after')
    def validate_total_score(self) -> Self:
        if self.total_score is not None:
            if self.total_score < 0 or self.total_score > 100:
                raise ValueError('총점은 0-100 사이여야 합니다.')
            if self.total_score.as_tuple().exponent < -2:
                raise ValueError('총점은 소수점 2자리까지만 허용됩니다.')
        return self

# =====================================================
# 텍스트 파싱 관련 모델 (archive.py 출력 파싱용)
# =====================================================

class ScoreTableRow(BaseModel):
    """점수 표에서 추출된 행 데이터"""
    category: str = Field(..., description="대분류명")
    section: Optional[str] = Field(None, description="소분류명 (있는 경우)")
    max_score: int = Field(..., description="만점")
    score: int = Field(..., description="획득 점수")
    minimum_required: Optional[int] = Field(None, description="최소 득점 기준")
    passed: Optional[bool] = Field(None, description="최소 득점 충족 여부")

class TextAnalysisResult(BaseModel):
    """archive.py 텍스트 분석 결과 파싱"""
    score_table: List[ScoreTableRow] = Field(default_factory=list, description="점수 표 데이터")
    strengths: List[str] = Field(default_factory=list, description="강점 목록")
    weaknesses: List[str] = Field(default_factory=list, description="약점 목록")
    improvements: List[str] = Field(default_factory=list, description="개선 제안")
    overall_assessment: Optional[str] = Field(None, description="종합 의견")

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

def calculate_category_score(section_scores: Dict[str, Decimal], category_name: str) -> Decimal:
    """카테고리별 총점 계산"""
    category_info = get_category_info(category_name)
    if not category_info:
        return Decimal('0.0')
    
    total_score = Decimal('0.0')
    for section_name in category_info["sections"]:
        if section_name in section_scores:
            total_score += section_scores[section_name]
    
    return total_score

def check_minimum_requirements(category_scores: Dict[str, Decimal]) -> Dict[str, bool]:
    """각 카테고리별 최소 기준 통과 여부 확인 (예비창업패키지 최소 득점기준)"""
    results = {}
    for category_name, category_info in EVALUATION_CATEGORIES.items():
        if category_name in category_scores:
            score = category_scores[category_name]
            minimum = Decimal(str(category_info["minimum_required"]))
            results[category_name] = score >= minimum
        else:
            results[category_name] = False
    
    return results

def is_risk_of_rejection(category_scores: Dict[str, Decimal]) -> bool:
    """탈락 위험도 판정"""
    minimum_checks = check_minimum_requirements(category_scores)
    return not all(minimum_checks.values())

def get_failed_categories(category_scores: Dict[str, Decimal]) -> List[str]:
    """최소 기준 미달 카테고리 목록"""
    minimum_checks = check_minimum_requirements(category_scores)
    return [category for category, passed in minimum_checks.items() if not passed]

# =====================================================
# 텍스트 파싱 헬퍼 함수들 (archive.py 출력 파싱용)
# =====================================================

def parse_gemini_analysis(analysis_text: str) -> TextAnalysisResult:
    """Gemini 분석 텍스트를 구조화된 데이터로 파싱"""
    lines = analysis_text.split('\n')
    result = TextAnalysisResult()
    
    current_section = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 점수 표 파싱 (간단한 예시)
        if '|' in line and ('점' in line or '충족' in line):
            # 실제 구현시 정규식이나 더 정교한 파싱 필요
            pass
            
        # 강점 섹션
        if '강점' in line and 'Strengths' in line:
            current_section = 'strengths'
        # 약점 섹션  
        elif '약점' in line or '개선' in line:
            current_section = 'weaknesses'
        # 개선 제안 섹션
        elif '개선 제안' in line:
            current_section = 'improvements'
        # 불릿 포인트 추출
        elif line.startswith('*') or line.startswith('-'):
            content = line[1:].strip()
            if current_section == 'strengths':
                result.strengths.append(content)
            elif current_section == 'weaknesses':
                result.weaknesses.append(content)
            elif current_section == 'improvements':
                result.improvements.append(content)
    
    return result

def extract_scores_from_analysis(analysis_text: str) -> Dict[str, int]:
    """분석 텍스트에서 점수 추출"""
    import re
    
    scores = {}
    # 표 형태의 점수 추출 (정규식 패턴)
    # 예: | 1.1. 창업아이템의 개발동기 | 15 | 13 |
    pattern = r'\|\s*([^|]+)\s*\|\s*\d+\s*\|\s*(\d+)\s*\|'
    
    for match in re.finditer(pattern, analysis_text):
        section_name = match.group(1).strip()
        score = int(match.group(2))
        scores[section_name] = score
    
    return scores

# =====================================================
# DB 저장용 헬퍼 함수들 (analysis_results.details JSONB 연동)
# =====================================================

def evaluation_response_to_db_json(response: EvaluationResponse) -> Dict[str, Any]:
    """EvaluationResponse를 analysis_results.details JSONB 저장용 딕셔너리로 변환"""
    data = response.model_dump(exclude_none=True)
    return _convert_decimals_to_float(data)

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

def _convert_decimals_to_float(obj: Any) -> Any:
    """Decimal 객체를 float로 재귀적으로 변환"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: _convert_decimals_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimals_to_float(item) for item in obj]
    else:
        return obj