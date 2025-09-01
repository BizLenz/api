# src/app/test/test_evaluation.py
import pytest
from decimal import Decimal
from app.schemas.evaluation import (
    EvaluationResponse,
    SectionResult,
    CategoryResult,
    get_section_max_score,
    get_category_info,
    calculate_category_score,
    check_minimum_requirements,
    is_risk_of_rejection,
    get_failed_categories,
    map_analysis_status_to_korean,
    map_korean_status_to_analysis,
    evaluation_response_to_db_json,
    db_json_to_evaluation_response,
    get_all_sections,
)

# =====================================================
# 1단계: 기본 헬퍼 함수들
# =====================================================

def test_get_section_max_score():
    """섹션별 최대 점수 반환 테스트"""
    assert get_section_max_score("1.1. 창업아이템의 개발동기") == 15
    assert get_section_max_score("1.2. 창업아이템의 목적(필요성)") == 15
    assert get_section_max_score("4.1. 대표자 및 팀원의 보유역량") == 20
    assert get_section_max_score("존재하지않는섹션") == 0
    assert get_section_max_score("") == 0

def test_calculate_category_score():
    """카테고리별 점수 계산 테스트"""
    # 문제인식 카테고리 (30점 만점)
    section_scores = {
        "1.1. 창업아이템의 개발동기": Decimal("12.0"),
        "1.2. 창업아이템의 목적(필요성)": Decimal("8.0")
    }
    score = calculate_category_score(section_scores, "문제인식")
    assert score == Decimal("20.0")
    
    # 해결방안 카테고리 (30점 만점)
    section_scores2 = {
        "2.1. 창업아이템의 사업화 전략": Decimal("15.0"),
        "2.2. 시장분석 및 경쟁력 확보방안": Decimal("10.0")
    }
    score2 = calculate_category_score(section_scores2, "해결방안")
    assert score2 == Decimal("25.0")
    
    # 존재하지 않는 카테고리
    assert calculate_category_score(section_scores, "존재하지않는카테고리") == Decimal("0.0")

# =====================================================
# 2단계: 검증 함수들
# =====================================================

def test_get_category_info():
    """카테고리 정보 반환 테스트"""
    info = get_category_info("문제인식")
    assert info["max_score"] == 30
    assert info["minimum_required"] == 18
    assert len(info["sections"]) == 2
    
    team_info = get_category_info("팀구성")
    assert team_info["max_score"] == 20
    assert team_info["minimum_required"] == 12
    
    empty_info = get_category_info("존재하지않는카테고리")
    assert empty_info == {}

def test_check_minimum_requirements():
    """최소 기준 통과 테스트"""
    category_scores = {
        "문제인식": Decimal("20.0"),
        "해결방안": Decimal("15.0"),
        "성장전략": Decimal("15.0"),
        "팀구성": Decimal("10.0"),
    }
    results = check_minimum_requirements(category_scores)
    assert results["문제인식"] is True
    assert results["해결방안"] is False
    assert results["성장전략"] is True
    assert results["팀구성"] is False

def test_is_risk_of_rejection():
    """탈락 위험도 판정 테스트"""
    passing_scores = {
        "문제인식": Decimal("25.0"),
        "해결방안": Decimal("20.0"),
        "성장전략": Decimal("15.0"),
        "팀구성": Decimal("18.0"),
    }
    assert is_risk_of_rejection(passing_scores) is False
    
    failing_scores = {
        "문제인식": Decimal("10.0"),
        "해결방안": Decimal("25.0"),
        "성장전략": Decimal("8.0"),
        "팀구성": Decimal("15.0"),
    }
    assert is_risk_of_rejection(failing_scores) is True

def test_get_failed_categories():
    """최소 기준 미달 카테고리 목록 테스트"""
    category_scores = {
        "문제인식": Decimal("10.0"),
        "해결방안": Decimal("25.0"),
        "성장전략": Decimal("8.0"),
        "팀구성": Decimal("15.0"),
    }
    failed = get_failed_categories(category_scores)
    assert "문제인식" in failed
    assert "해결방안" not in failed
    assert "성장전략" in failed
    assert "팀구성" not in failed
    assert len(failed) == 2

# =====================================================
# 3단계: Pydantic 모델 검증
# =====================================================

def test_section_result_validation():
    """SectionResult 점수 검증 테스트"""
    section = SectionResult(score=Decimal("10.0"), max_score=15)
    assert section.score == Decimal("10.0")
    assert section.max_score == 15
    
    section_max = SectionResult(score=Decimal("15.0"), max_score=15)
    assert section_max.score == Decimal("15.0")
    
    section_zero = SectionResult(score=Decimal("0.0"), max_score=15)
    assert section_zero.score == Decimal("0.0")
    
    with pytest.raises(ValueError):
        SectionResult(score=Decimal("20.0"), max_score=15)
    with pytest.raises(ValueError):
        SectionResult(score=Decimal("-5.0"), max_score=15)

def test_category_result_model():
    """CategoryResult 모델 테스트"""
    category = CategoryResult(
        score=Decimal("25.0"),
        max_score=30,
        minimum_required=18,
        passed=True,
        sections=["섹션1", "섹션2"],
    )
    assert category.score == Decimal("25.0")
    assert category.passed is True

def test_evaluation_response_model():
    """EvaluationResponse 모델 테스트"""
    response = EvaluationResponse(
        success=True,
        total_score=Decimal("85.5"),
        overall_strengths=["강점1", "강점2"],
        overall_weaknesses=["약점1", "약점2", "약점3"],
        risk_of_rejection=False,
    )
    assert response.success is True
    assert response.total_score == Decimal("85.5")
    assert len(response.overall_strengths) == 2
    assert len(response.overall_weaknesses) == 3
    assert response.risk_of_rejection is False

    error_response = EvaluationResponse(
        success=False,
        error_message="평가 실패",
        total_score=None,
    )
    assert error_response.success is False
    assert error_response.error_message == "평가 실패"
    assert error_response.total_score is None

def test_map_analysis_status_to_korean():
    """DB 상태값을 한국어로 변환 테스트"""
    assert map_analysis_status_to_korean("pending") == "대기중"
    assert map_analysis_status_to_korean("processing") == "분석중"
    assert map_analysis_status_to_korean("completed") == "완료"
    assert map_analysis_status_to_korean("failed") == "실패"
    assert map_analysis_status_to_korean("unknown") == "unknown"

def test_map_korean_status_to_analysis():
    """한국어 상태값을 DB 상태값으로 변환 테스트"""
    assert map_korean_status_to_analysis("대기중") == "pending"
    assert map_korean_status_to_analysis("분석중") == "processing"
    assert map_korean_status_to_analysis("완료") == "completed"
    assert map_korean_status_to_analysis("실패") == "failed"
    assert map_korean_status_to_analysis("알수없음") == "알수없음"

def test_evaluation_response_to_db_json():
    """EvaluationResponse를 딕셔너리로 변환 테스트"""
    response = EvaluationResponse(
        success=True,
        total_score=Decimal("85.5"),
        overall_strengths=["강점1", "강점2"],
    )
    json_data = evaluation_response_to_db_json(response)
    assert json_data["success"] is True
    assert json_data["total_score"] == 85.5
    assert "overall_strengths" in json_data

def test_db_json_to_evaluation_response():
    """딕셔너리를 EvaluationResponse로 변환 테스트"""
    json_data = {
        "success": True,
        "total_score": 75.0,
        "overall_weaknesses": ["약점1", "약점2", "약점3"],
    }
    response = db_json_to_evaluation_response(json_data)
    assert response.success is True
    assert response.total_score == 75.0
    assert len(response.overall_weaknesses) == 3

def test_get_all_sections():
    """모든 평가 섹션 목록 반환 테스트"""
    sections = get_all_sections()
    assert len(sections) == 7
    assert "1.1. 창업아이템의 개발동기" in sections
    assert "4.1. 대표자 및 팀원의 보유역량" in sections
