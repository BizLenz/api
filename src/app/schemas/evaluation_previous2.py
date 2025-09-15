# src/app/schemas/evaluation_v2.py
import json
import os
from typing import Dict, Any, List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

# =====================================================
# JSON 파일 로딩 함수
# =====================================================

def load_prompts_from_json() -> Dict[str, Any]:
    """JSON 파일에서 프롬프트 데이터 로드"""
    try:
        # 현재 파일 기준으로 prompts.json 찾기
        current_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(current_dir, "prompts.json")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: prompts.json not found at {current_dir}/prompts.json")
        return {
            "system_prompt": "",
            "section_analysis_template": "",
            "final_report_template": "",
            "questions": {}
        }
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파일 파싱 오류: {str(e)}")

# =====================================================
# 평가 기준 상수 정의 (예비창업패키지 기준)
# =====================================================

EVALUATION_CATEGORIES = {
    "1. 문제인식": {
        "max_score": 30,
        "minimum_required": 18,
        "sections": ["1.1. 창업아이템의 개발동기", "1.2. 창업아이템의 목적(필요성)"]
    },
    "2. 해결방안": {
        "max_score": 30,
        "minimum_required": 18,
        "sections": ["2.1. 창업아이템의 사업화 전략", "2.2. 시장분석 및 경쟁력 확보방안"]
    },
    "3. 성장전략": {
        "max_score": 20,
        "minimum_required": 12,
        "sections": ["3.1. 자금소요 및 조달계획", "3.2. 시장진입 및 성과창출 전략"]
    },
    "4. 팀 구성": {
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

def get_evaluation_criteria_with_questions() -> List[Dict[str, Any]]:
    """JSON에서 질문을 로드해서 EVALUATION_CRITERIA와 결합"""
    prompt_data = load_prompts_from_json()
    questions_data = prompt_data.get("questions", {})
    
    return [
        {
            "section_name": "1.1. 창업아이템의 개발동기",
            "main_category": "1. 문제인식",
            "category_max_score": 30,
            "category_min_score": 18,
            "max_score": 15,
            "pillars": {
                "문제 발견의 진정성 및 구체성 (5점)": {
                    "description": "창업 아이템의 문제 발견 계기가 개인의 경험/관찰에서 출발하여 구체적이고 진정성 있게 기술되었으며, 창업자의 통찰력과 연결되어 있는가?",
                    "questions": questions_data.get("1.1", {}).get("문제 발견의 진정성 및 구체성 (5점)", [])
                },
                "문제의 객관적 검증 및 보편성 (5점)": {
                    "description": "발견된 문제가 단순한 개인적 불편함을 넘어, 시장 조사, 데이터, 이해관계자 의견 등 객관적인 근거를 통해 그 보편성과 심각성이 충분히 검증되었는가?",
                    "questions": questions_data.get("1.1", {}).get("문제의 객관적 검증 및 보편성 (5점)", [])
                },
                "해결의 시급성 및 사업적 가치 (5점)": {
                    "description": "발견된 문제 해결의 시급성과 그로 인해 창출될 사업적 가치가 논리적이고 현실적으로 설명되었으며, 기존 시도와의 차별점이 명확하게 제시되었는가?",
                    "questions": questions_data.get("1.1", {}).get("해결의 시급성 및 사업적 가치 (5점)", [])
                }
            },
        },
        {
            "section_name": "1.2. 창업아이템의 목적(필요성)",
            "main_category": "1. 문제인식",
            "category_max_score": 30,
            "category_min_score": 18,
            "max_score": 15,
            "pillars": {
                "핵심 문제 정의 및 고객 Pain Point 분석 (5점)": {
                    "description": "창업 아이템이 해결하고자 하는 핵심 문제가 명확하게 정의되고, 목표 고객층의 구체적인 Pain Point 및 현재 해결 방안의 한계를 깊이 있게 이해하고 있는가?",
                    "questions": questions_data.get("1.2", {}).get("핵심 문제 정의 및 고객 Pain Point 분석 (5점)", [])
                },
                "시장 필요성 및 가치 제안의 구체성 (5점)": {
                    "description": "창업 아이템의 필요성을 뒷받침하는 시장 트렌드, 데이터 분석이 명확하며, 이 아이템이 가져올 수 있는 사회적, 경제적, 환경적 임팩트 및 장기적인 가치가 구체적으로 제시되었는가?",
                    "questions": questions_data.get("1.2", {}).get("시장 필요성 및 가치 제안의 구체성 (5점)", [])
                },
                "차별화된 해결 방안 및 비전 제시 (5점)": {
                    "description": "경쟁 제품/서비스 대비 이 아이템의 핵심 차별점이 명확하며, 문제를 해결하는 창업가의 통찰력과 일관된 비전이 제시되고 있는가?",
                    "questions": questions_data.get("1.2", {}).get("차별화된 해결 방안 및 비전 제시 (5점)", [])
                }
            }
        },
        {
            "section_name": "2.1. 창업아이템의 사업화 전략",
            "main_category": "2. 해결방안",
            "category_max_score": 30,
            "category_min_score": 18,
            "max_score": 15,
            "pillars": {
                "제품/서비스 기술성 및 구현 계획 (5점)": {
                    "description": "창업 아이템의 핵심 기술 요소가 명확히 정의되고, 그 구현 방식과 개발 역량이 구체적으로 제시되었으며, 사업화 전략에 부합하는 개발 계획이 수립되어 있는가?",
                    "questions": questions_data.get("2.1", {}).get("제품/서비스 기술성 및 구현 계획 (5점)", [])
                },
                "시장 출시 및 사용자 검증 전략 (5점)": {
                    "description": "제품/서비스의 구체적인 사용 시나리오가 제시되고, 초기 시장 출시를 위한 실험/프로토타입/MVP 개발 및 사용자 검증 계획이 명확하며, 고객 불편 사항에 대한 고려가 이루어졌는가?",
                    "questions": questions_data.get("2.1", {}).get("시장 출시 및 사용자 검증 전략 (5점)", [])
                },
                "사업화 성과 목표 및 관리 계획 (5점)": {
                    "description": "사업 기간 내 실현 가능한 성과 목표가 구체적으로 제시되었으며, 개발 완료 후의 테스트, 유지보수, 그리고 장기적인 확장 및 상용화 방안이 체계적으로 수립되어 있는가?",
                    "questions": questions_data.get("2.1", {}).get("사업화 성과 목표 및 관리 계획 (5점)", [])
                }
            }
        },
        {
            "section_name": "2.2. 시장분석 및 경쟁력 확보방안",
            "main_category": "2. 해결방안",
            "category_max_score": 30,
            "category_min_score": 18,
            "max_score": 15,
            "pillars": {
                "경쟁 환경 분석 및 차별화 전략 (5점)": {
                    "description": "핵심 경쟁사들의 기술적 특성, 강점 및 약점에 대한 깊이 있는 분석을 바탕으로, 창업 아이템의 명확한 경쟁 우위와 차별화 전략이 구체적으로 제시되었는가?",
                    "questions": questions_data.get("2.2", {}).get("경쟁 환경 분석 및 차별화 전략 (5점)", [])
                },
                "시장 침투 및 확장 가능성 (5점)": {
                    "description": "창업 아이템의 초기 고객 도입 장벽을 낮추고 시장에 성공적으로 침투하기 위한 전략이 명확하며, 향후 다양한 산업 및 프리미엄 시장으로의 확장 가능성과 수익 모델이 구체적으로 제시되었는가?",
                    "questions": questions_data.get("2.2", {}).get("시장 침투 및 확장 가능성 (5점)", [])
                },
                "기술 및 시장 지속성 전략 (5점)": {
                    "description": "아이템 기술의 수명 주기 및 시장 내 지속성에 대한 명확한 분석을 바탕으로, 장기적인 경쟁 우위를 유지하기 위한 대응 전략과 경제적 가치 분석이 수립되어 있는가?",
                    "questions": questions_data.get("2.2", {}).get("기술 및 시장 지속성 전략 (5점)", [])
                }
            }
        },
        {
            "section_name": "3.1. 자금소요 및 조달계획",
            "main_category": "3. 성장전략",
            "category_max_score": 20,
            "category_min_score": 12,
            "max_score": 10,
            "pillars": {
                "수익 모델 및 비용 구조의 이해 (3점)": {
                    "description": "창업 아이템의 주요 수익 모델이 명확하게 정의되고, 사업 운영에 있어 가장 큰 비중을 차지하는 비용 항목을 인지하고 있으며, 이에 대한 관리 방안이 구체적으로 제시되었는가?",
                    "questions": questions_data.get("3.1", {}).get("수익 모델 및 비용 구조의 이해 (3점)", [])
                },
                "구체적인 자금 소요 및 조달 계획 (4점)": {
                    "description": "초기 자금 소요액이 명확하게 제시되고, 항목별 자금 사용 계획이 구체적으로 산출되었으며, 필요한 외부 자금 조달 계획 및 그 규모가 현실적으로 수립되어 있는가?",
                    "questions": questions_data.get("3.1", {}).get("구체적인 자금 소요 및 조달 계획 (4점)", [])
                },
                "재정 리스크 관리 및 대응 전략 (3점)": {
                    "description": "예상 가능한 재정적 리스크 요인이 식별되었고, 계획한 매출 미달성 또는 자금 조달 실패 시의 구체적인 대응 전략 및 비즈니스 모델 변경 계획이 체계적으로 마련되어 있는가?",
                    "questions": questions_data.get("3.1", {}).get("재정 리스크 관리 및 대응 전략 (3점)", [])
                }
            }
        },
        {
            "section_name": "3.2. 시장진입 및 성과창출 전략",
            "main_category": "3. 성장전략",
            "category_max_score": 20,
            "category_min_score": 12,
            "max_score": 10,
            "pillars": {
                "수익 모델의 구체성 및 가격 정책 (4점)": {
                    "description": "창업 아이템의 비즈니스 모델과 주요 수익 모델이 명확히 제시되고, 수익 모델별 예상 매출 비중, 가격 정책, 그리고 손익분기점에 대한 구체적인 분석이 이루어졌는가?",
                    "questions": questions_data.get("3.2", {}).get("수익 모델의 구체성 및 가격 정책 (4점)", [])
                },
                "시장 진입 및 고객 확보/유지 전략 (3점)": {
                    "description": "초기 고객 확보를 위한 마케팅 전략이 구체적으로 수립되었으며, 고객 획득 비용, 재구매율/유지율 목표 및 이를 달성하기 위한 전략이 명확하게 제시되었는가?",
                    "questions": questions_data.get("3.2", {}).get("시장 진입 및 고객 확보/유지 전략 (3점)", [])
                },
                "사업 리스크 관리 방안 (3점)": {
                    "description": "사업 추진 과정에서 발생 가능한 주요 리스크 요인이 식별되었고, 각 리스크별 대응 시나리오, 우선순위, 그리고 리스크 현실화 시의 영향 및 모니터링 체계가 체계적으로 수립되어 있는가?",
                    "questions": questions_data.get("3.2", {}).get("사업 리스크 관리 방안 (3점)", [])
                }
            }
        },
        {
            "section_name": "4.1. 대표자 및 팀원의 보유역량",
            "main_category": "4. 팀 구성",
            "category_max_score": 20,
            "category_min_score": 12,
            "max_score": 20,
            "pillars": {
                "팀원의 개별 역량 및 역할 분담 (7점)": {
                    "description": "대표자 및 팀원 각자의 핵심 역량과 담당 업무가 구체적이며 중복 없이 분배되어 있고, 과거 유사 프로젝트 수행 경험을 통해 사업 추진에 필요한 전문성을 충분히 보유하고 있는가?",
                    "questions": questions_data.get("4.1", {}).get("팀원의 개별 역량 및 역할 분담 (7점)", [])
                },
                "팀 운영 및 의사소통 체계 (6점)": {
                    "description": "팀 내 효율적인 의사결정 방식, 커뮤니케이션 채널, 정보 공유 시스템이 체계적으로 구축되어 있으며, 팀원들의 동기 부여 및 갈등 해결 방안이 마련되어 있는가?",
                    "questions": questions_data.get("4.1", {}).get("팀 운영 및 의사소통 체계 (6점)", [])
                },
                "외부 역량 활용 및 팀 관련 리스크 관리 (7점)": {
                    "description": "팀 내부 역량의 한계를 보완하기 위한 외부 전문가, 자문단, 협력사와의 협업 계획이 구체적이며, 핵심 인력 이탈, 정보 유출 등 팀 관련 리스크에 대한 실질적인 대응 방안이 수립되어 있는가?",
                    "questions": questions_data.get("4.1", {}).get("외부 역량 활용 및 팀 관련 리스크 관리 (7점)", [])
                }
            }
        }
    ]

# =====================================================
# Pydantic 모델 정의 (main.py JSON 구조 기준)
# =====================================================

class SubCriteria(BaseModel):
    """하위 평가 기준 (섹션별 점수)"""
    name: str = Field(..., description="섹션명")
    score: float = Field(..., description="섹션 점수")

class CategoryResult(BaseModel):
    """카테고리별 평가 결과"""
    category: str = Field(..., description="카테고리명")
    score: float = Field(..., description="카테고리 총점")
    max_score: int = Field(..., description="카테고리 최대 점수")
    min_score_required: int = Field(..., description="최소 득점 기준")
    is_passed: bool = Field(..., description="최소 기준 통과 여부")
    sub_criteria: List[SubCriteria] = Field(..., description="하위 섹션별 점수")
    reasoning: str = Field(..., description="점수 산정 근거")

class FinalReportResponse(BaseModel):
    """Gemini가 생성하는 최종 평가 보고서 JSON 구조"""
    title: str = Field(default="예비창업패키지 사업계획서 최종 평가 보고서", description="보고서 제목")
    total_score: float = Field(..., description="총점 (0-100)", ge=0, le=100)
    overall_assessment: str = Field(..., description="전체 평가")
    strengths: List[str] = Field(..., description="주요 강점")
    weaknesses: List[str] = Field(..., description="주요 약점")
    improvement_suggestions: List[str] = Field(..., description="개선 제안사항")
    evaluation_criteria: List[CategoryResult] = Field(..., description="카테고리별 평가 결과")

    @model_validator(mode='after')
    def validate_total_score(self) -> Self:
        """총점 검증"""
        if self.total_score < 0 or self.total_score > 100:
            raise ValueError('총점은 0-100 사이여야 합니다.')
        return self

class SectionAnalysisResult(BaseModel):
    """개별 섹션 분석 결과 (DB 저장용)"""
    section_name: str = Field(..., description="섹션명")
    analysis_text: str = Field(..., description="Gemini 분석 내용")
    is_failed: bool = Field(default=False, description="분석 실패 여부")

class EvaluationRequest(BaseModel):
    """사업계획서 평가 요청"""
    business_plan_id: int = Field(..., description="사업계획서 ID")
    additional_info: Optional[str] = Field(None, description="추가 정보", max_length=500)

class EvaluationResponse(BaseModel):
    """평가 완료 응답"""
    success: bool = Field(..., description="평가 성공 여부")
    analysis_job_id: Optional[int] = Field(None, description="분석 작업 ID")
    analysis_result_id: Optional[int] = Field(None, description="분석 결과 ID")
    error_message: Optional[str] = Field(None, description="에러 메시지")
    final_report: Optional[FinalReportResponse] = Field(None, description="최종 평가 보고서")

# =====================================================
# 헬퍼 함수들 (main.py 기준)
# =====================================================

def get_section_max_score(section_name: str) -> int:
    """섹션명으로 최대 점수 반환"""
    return SECTION_SCORES.get(section_name, 0)

def get_category_info(category_name: str) -> Dict[str, Any]:
    """카테고리명으로 정보 반환"""
    return EVALUATION_CATEGORIES.get(category_name, {})

def get_all_categories() -> List[str]:
    """모든 카테고리 목록 반환"""
    return list(EVALUATION_CATEGORIES.keys())

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
    """각 카테고리별 최소 기준 통과 여부 확인"""
    results = {}
    for category_name, category_info in EVALUATION_CATEGORIES.items():
        if category_name in category_scores:
            score = category_scores[category_name]
            minimum = Decimal(str(category_info["minimum_required"]))
            results[category_name] = score >= minimum
        else:
            results[category_name] = False
    
    return results

def validate_final_report(report: Dict[str, Any]) -> FinalReportResponse:
    """Gemini 응답을 FinalReportResponse로 검증 및 변환"""
    try:
        return FinalReportResponse(**report)
    except Exception as e:
        raise ValueError(f"Gemini 응답 형식이 올바르지 않습니다: {str(e)}")

def create_section_analysis_prompt(criteria: Dict[str, Any]) -> str:
    """개별 섹션 분석용 프롬프트 생성 (main.py 방식)"""
    prompt_data = load_prompts_from_json()
    section_prompt_template = prompt_data.get("section_analysis_template", "")
    
    section_name = criteria["section_name"]
    max_score = criteria["max_score"]
    
    # Pillar 정보를 프롬프트에 맞게 가공 (main.py와 동일한 방식)
    pillars_description = []
    pillar_scoring_format = []
    
    for pillar_name, pillar_data in criteria["pillars"].items():
        # Pillar 설명 부분 생성
        questions_str = "\n".join([f"  - {q}" for q in pillar_data.get("questions", [])])
        pillars_description.append(
            f"- **{pillar_name}:** {pillar_data['description']}\n"
            f"  **[세부 검토사항]**\n{questions_str}"
        )

        # 모델이 채워야 할 채점 형식 부분 생성
        pillar_scoring_format.append(
            f"- **{pillar_name}:**\n"
            f"  - **분석:** [사업계획서의 관련 내용을 여기에 분석/요약]\n"
            f"  - **점수:** [루브릭에 따른 점수] / {pillar_name.split('(')[-1].replace('점)', '').strip()}점\n"
            f"  - **근거:** [점수 부여에 대한 구체적인 이유]"
        )

    # 가공된 정보를 사용하여 프롬프트 완성
    return section_prompt_template.format(
        section_name=section_name,
        max_score=max_score,
        pillars_description="\n    ".join(pillars_description),
        pillar_scoring_format="\n".join(pillar_scoring_format),
    )

def create_final_report_prompt(individual_analyses: List[SectionAnalysisResult]) -> str:
    """최종 보고서 생성용 프롬프트 생성 (main.py 방식)"""
    prompt_data = load_prompts_from_json()
    final_prompt_template = prompt_data.get("final_report_template", "")
    
    structured_input_parts = []
    evaluation_criteria = get_evaluation_criteria_with_questions()
    
    for result in individual_analyses:
        # criteria 정보 찾기
        criteria = None
        for crit in evaluation_criteria:
            if crit["section_name"] == result.section_name:
                criteria = crit
                break
        
        if criteria:
            structured_input_parts.append(
                f"<item>\n"
                f"<metadata>\n"
                f"  section_name: {criteria['section_name']}\n"
                f"  main_category: {criteria['main_category']}\n"
                f"  category_max_score: {criteria['category_max_score']}\n"
                f"  category_min_score: {criteria['category_min_score']}\n"
                f"</metadata>\n"
                f"<analysis>\n{result.analysis_text}\n</analysis>\n"
                f"</item>"
            )
    
    structured_analyses_input = "\n\n".join(structured_input_parts)
    
    return final_prompt_template.format(
        structured_analyses_input=structured_analyses_input
    )

def get_system_prompt() -> str:
    """시스템 프롬프트 반환"""
    prompt_data = load_prompts_from_json()
    return prompt_data.get("system_prompt", "")

# =====================================================
# DB 저장용 함수들
# =====================================================

def final_report_to_db_details(report: FinalReportResponse) -> Dict[str, Any]:
    """FinalReportResponse를 DB details JSONB 저장용으로 변환"""
    return report.model_dump(exclude_none=True)

def db_details_to_final_report(details: Dict[str, Any]) -> FinalReportResponse:
    """DB details에서 FinalReportResponse로 변환"""
    return FinalReportResponse(**details)

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

# =====================================================
# main.py 기반 프롬프트 상수 정의
# =====================================================

SYSTEM_PROMPT = """
당신은 '예비창업패키지' 전문 심사위원입니다. 당신의 유일한 임무는 제출된 사업계획서를 평가 기준에 따라 엄격하고 객관적으로 분석하는 것입니다.
- 모든 평가는 제공된 사업계획서 내용에만 근거해야 합니다. 절대 정보를 추측하거나 가정하지 마십시오.
- 분석은 비판적이어야 하며, 각 점수에 대한 명확한 근거를 제시해야 합니다.
- 감정적이거나 모호한 표현을 배제하고, 강점, 약점, 개선점을 명확하고 단호한 어조로 기술하십시오.
'예비창업패키지'의 평가 기준은 다음과 같습니다:
문제인식
1.1. 창업아이템의 개발동기: 15점
1.2. 창업아이템의 목적(필요성): 15점
소계: 30점, 최소 득점기준: 18점
해결방안
2.1. 창업아이템의 사업화 전략: 15점
2.2. 시장분석 및 경쟁력 확보방안: 15점
소계: 30점, 최소 득점기준: 18점
성장전략
3.1. 자금소요 및 조달계획: 10점
3.2. 시장진입 및 성과창출 전략: 10점
소계: 20점, 최소 득점기준: 12점
팀 구성
4.1. 대표자 및 팀원의 보유역량: 20점
소계: 20점, 최소 득점기준: 12점
"""

SECTION_ANALYSIS_PROMPT_TEMPLATE = """
**평가 항목:** {section_name}
**최대 점수:** {max_score}점

**지시:** 아래 각 평가 Pillar에 대해 사업계획서 내용을 분석하고, 루브릭에 따라 점수를 부여하시오. 평가는 단호하고 명확해야 함.

**[평가 Pillar]**
{pillars_description}

**[Scoring Rubric]**
- **우수 (100%):** 모든 요구사항을 구체적인 근거와 데이터를 통해 명확하게 충족함.
- **보통 (70%):** 핵심 내용은 포함되어 있으나, 설명이 추상적이거나 근거가 부족함.
- **미흡 (30%):** 내용이 거의 없거나, 질문과 무관한 내용만 기술되어 있음.
- **없음 (0%):** 관련 내용을 전혀 찾을 수 없음.

---
**[분석 및 평가 결과]**

**1. Pillar 별 분석 및 채점:**
{pillar_scoring_format}

**2. 최종 점수 및 요약:**
- **최종 점수:** [산출된 총점] / {max_score}
- **강점:** [이 항목의 핵심 강점 1가지]
- **약점 및 개선 필요사항:** [가장 시급하게 개선해야 할 점 1-2가지]
"""

FINAL_REPORT_PROMPT = """
당신은 최종 평가 보고서를 작성하는 시스템입니다.
아래에 제공된 각 항목별 분석 결과와 메타데이터를 종합하여, 반드시 유효한 JSON 형식으로 최종 보고서를 생성하십시오.
JSON 객체 외에 다른 설명이나 텍스트를 절대 추가하지 마십시오.

---
[개별 항목 분석 데이터]
{structured_analyses_input}
---

[JSON 출력 형식]
- `title`: "예비창업패키지 사업계획서 최종 평가 보고서"로 고정.
- `total_score`: 모든 하위 항목 점수의 총합.
- `overall_assessment`: 모든 대분류가 '최소 득점기준'을 통과했는지 여부에 따라 "통과 가능" 또는 "탈락 가능성 높음"으로 결정. 하나라도 미충족 시 '탈락 가능성 높음'.
- `strengths`: 전체 분석에서 가장 중요하고 반복적으로 언급된 강점 2-3개를 요약.
- `weaknesses`: 전체 분석에서 가장 결정적인 약점 3-5개를 요약.
- `improvement_suggestions`: 식별된 약점을 해결하기 위한 가장 구체적이고 실행 가능한 제안 3가지를 제시.
- `evaluation_criteria`: 4개의 대분류로 구성.
    - `category`: 메타데이터의 `main_category` 값을 사용.
    - `score`: 해당 대분류에 속한 하위 항목들의 점수 합계.
    - `max_score`, `min_score_required`: 메타데이터의 `category_max_score`, `category_min_score` 값을 **그대로 사용**. (추론 금지)
    - `is_passed`: `score`가 `min_score_required` 이상인지 여부를 boolean (true/false) 값으로 표시.
    - `sub_criteria`: 각 하위 항목의 이름과 점수를 포함하는 객체 배열. 분석 실패 시 점수는 0점으로 처리.
    - `reasoning`: 해당 대분류의 점수에 대한 핵심적인 이유를 요약. 강점과 약점을 모두 포함하여 단호하게 기술.

[JSON 출력 시작]
"""

# =====================================================
# 기본 프롬프트 사용 함수들 (fallback)
# =====================================================

def get_system_prompt_fallback() -> str:
    """JSON 파일이 없을 때 사용할 기본 시스템 프롬프트"""
    return SYSTEM_PROMPT

def get_section_analysis_prompt_fallback() -> str:
    """JSON 파일이 없을 때 사용할 기본 섹션 분석 프롬프트"""
    return SECTION_ANALYSIS_PROMPT_TEMPLATE

def get_final_report_prompt_fallback() -> str:
    """JSON 파일이 없을 때 사용할 기본 최종 보고서 프롬프트"""
    return FINAL_REPORT_PROMPT

# =====================================================
# 통합 프롬프트 생성 함수들
# =====================================================

def create_section_analysis_prompt_integrated(criteria: Dict[str, Any]) -> str:
    """섹션 분석 프롬프트 생성 (JSON 파일 우선, fallback 지원)"""
    # JSON에서 템플릿 시도
    prompt_data = load_prompts_from_json()
    template = prompt_data.get("section_analysis_template")
    
    # JSON 파일이 없거나 템플릿이 비어있으면 fallback 사용
    if not template:
        template = SECTION_ANALYSIS_PROMPT_TEMPLATE
    
    section_name = criteria["section_name"]
    max_score = criteria["max_score"]
    
    # Pillar 정보를 프롬프트에 맞게 가공
    pillars_description = []
    pillar_scoring_format = []
    
    for pillar_name, pillar_data in criteria["pillars"].items():
        questions_str = "\n".join([f"  - {q}" for q in pillar_data.get("questions", [])])
        pillars_description.append(
            f"- **{pillar_name}:** {pillar_data['description']}\n"
            f"  **[세부 검토사항]**\n{questions_str}"
        )

        pillar_scoring_format.append(
            f"- **{pillar_name}:**\n"
            f"  - **분석:** [사업계획서의 관련 내용을 여기에 분석/요약]\n"
            f"  - **점수:** [루브릭에 따른 점수] / {pillar_name.split('(')[-1].replace('점)', '').strip()}점\n"
            f"  - **근거:** [점수 부여에 대한 구체적인 이유]"
        )

    return template.format(
        section_name=section_name,
        max_score=max_score,
        pillars_description="\n    ".join(pillars_description),
        pillar_scoring_format="\n".join(pillar_scoring_format),
    )

def create_final_report_prompt_integrated(individual_analyses: List[SectionAnalysisResult]) -> str:
    """최종 보고서 프롬프트 생성 (JSON 파일 우선, fallback 지원)"""
    prompt_data = load_prompts_from_json()
    template = prompt_data.get("final_report_template")
    
    # JSON 파일이 없거나 템플릿이 비어있으면 fallback 사용
    if not template:
        template = FINAL_REPORT_PROMPT
    
    structured_input_parts = []
    evaluation_criteria = get_evaluation_criteria_with_questions()
    
    for result in individual_analyses:
        criteria = None
        for crit in evaluation_criteria:
            if crit["section_name"] == result.section_name:
                criteria = crit
                break
        
        if criteria:
            structured_input_parts.append(
                f"<item>\n"
                f"<metadata>\n"
                f"  section_name: {criteria['section_name']}\n"
                f"  main_category: {criteria['main_category']}\n"
                f"  category_max_score: {criteria['category_max_score']}\n"
                f"  category_min_score: {criteria['category_min_score']}\n"
                f"</metadata>\n"
                f"<analysis>\n{result.analysis_text}\n</analysis>\n"
                f"</item>"
            )
    
    structured_analyses_input = "\n\n".join(structured_input_parts)
    
    return template.format(structured_analyses_input=structured_analyses_input)

def get_system_prompt_integrated() -> str:
    """시스템 프롬프트 반환 (JSON 파일 우선, fallback 지원)"""
    prompt_data = load_prompts_from_json()
    system_prompt = prompt_data.get("system_prompt")
    
    # JSON 파일이 없거나 시스템 프롬프트가 비어있으면 fallback 사용
    if not system_prompt:
        return SYSTEM_PROMPT
    
    return system_prompt