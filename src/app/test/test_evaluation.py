# src/app/test/test_evaluation.py
import pytest
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
    # 정상적인 섹션들
    assert get_section_max_score("1.1. 창업아이템의 개발동기") == 15
    assert get_section_max_score("1.2. 창업아이템의 목적(필요성)") == 15
    assert get_section_max_score("4.1. 대표자 및 팀원의 보유역량") == 20
    
    # 존재하지 않는 섹션
    assert get_section_max_score("존재하지않는섹션") == 0
    assert get_section_max_score("") == 0

def test_calculate_category_score():
    """카테고리별 점수 계산 테스트"""
    # 문제인식 카테고리 (30점 만점)
    section_scores = {
        "1.1. 창업아이템의 개발동기": 12.0,
        "1.2. 창업아이템의 목적(필요성)": 8.0
    }
    score = calculate_category_score(section_scores, "문제인식")
    assert score == 20.0
    
    # 해결방안 카테고리 (30점 만점)
    section_scores2 = {
        "2.1. 창업아이템의 사업화 전략": 15.0,
        "2.2. 시장분석 및 경쟁력 확보방안": 10.0
    }
    score2 = calculate_category_score(section_scores2, "해결방안")
    assert score2 == 25.0
    
    # 존재하지 않는 카테고리
    assert calculate_category_score(section_scores, "존재하지않는카테고리") == 0.0

# =====================================================
# 2단계: 검증 함수들
# =====================================================

def test_get_category_info():
    """카테고리 정보 반환 테스트"""
    # 문제인식 카테고리
    info = get_category_info("문제인식")
    assert info["max_score"] == 30
    assert info["minimum_required"] == 18
    assert len(info["sections"]) == 2
    
    # 팀구성 카테고리
    team_info = get_category_info("팀구성")
    assert team_info["max_score"] == 20
    assert team_info["minimum_required"] == 12
    
    # 존재하지 않는 카테고리
    empty_info = get_category_info("존재하지않는카테고리")
    assert empty_info == {}

def test_check_minimum_requirements():
    """최소 기준 통과 테스트"""
    category_scores = {
        "문제인식": 20.0,  # 18점 이상 필요 - 통과
        "해결방안": 15.0,  # 18점 이상 필요 - 미통과
        "성장전략": 15.0,  # 12점 이상 필요 - 통과
        "팀구성": 10.0     # 12점 이상 필요 - 미통과
    }
    results = check_minimum_requirements(category_scores)
    
    assert results["문제인식"] == True
    assert results["해결방안"] == False
    assert results["성장전략"] == True
    assert results["팀구성"] == False

def test_is_risk_of_rejection():
    """탈락 위험도 판정 테스트"""
    # 모든 카테고리 통과
    passing_scores = {
        "문제인식": 25.0,
        "해결방안": 20.0,
        "성장전략": 15.0,
        "팀구성": 18.0
    }
    assert is_risk_of_rejection(passing_scores) == False
    
    # 일부 카테고리 미달
    failing_scores = {
        "문제인식": 10.0,  # 미달
        "해결방안": 25.0,
        "성장전략": 8.0,   # 미달
        "팀구성": 15.0
    }
    assert is_risk_of_rejection(failing_scores) == True

def test_get_failed_categories():
    """최소 기준 미달 카테고리 목록 테스트"""
    category_scores = {
        "문제인식": 10.0,  # 18점 필요 - 미달
        "해결방안": 25.0,  # 18점 필요 - 통과
        "성장전략": 8.0,   # 12점 필요 - 미달
        "팀구성": 15.0     # 12점 필요 - 통과
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
    # 올바른 점수
    section = SectionResult(score=10.0, max_score=15)
    assert section.score == 10.0
    assert section.max_score == 15
    
    # 경계값 테스트
    section_max = SectionResult(score=15.0, max_score=15)
    assert section_max.score == 15.0
    
    section_zero = SectionResult(score=0.0, max_score=15)
    assert section_zero.score == 0.0
    
    # 잘못된 점수 (범위 초과) - 이제 정상적으로 에러 발생
    with pytest.raises(ValueError):
        SectionResult(score=20.0, max_score=15)
    
    # 음수 점수는 ge=0 제약으로 이미 막힘
    with pytest.raises(ValueError):
        SectionResult(score=-5.0, max_score=15)

def test_category_result_model():
    """CategoryResult 모델 테스트"""
    category = CategoryResult(
        score=25.0,
        max_score=30,
        minimum_required=18,
        passed=True,
        sections=["섹션1", "섹션2"]
    )
    
    assert category.score == 25.0
    assert category.max_score == 30
    assert category.minimum_required == 18
    assert category.passed == True
    assert len(category.sections) == 2

def test_evaluation_response_model():
    """EvaluationResponse 모델 테스트"""
    response = EvaluationResponse(
        success=True,
        total_score=85.5,
        overall_strengths=["강점1", "강점2"],
        overall_weaknesses=["약점1", "약점2", "약점3"],
        risk_of_rejection=False
    )
    
    assert response.success == True
    assert response.total_score == 85.5
    assert len(response.overall_strengths) == 2
    assert len(response.overall_weaknesses) == 3
    assert response.risk_of_rejection == False
    
    # 에러 상황 테스트
    error_response = EvaluationResponse(
        success=False,
        error_message="평가 실패",
        total_score=None
    )
    
    assert error_response.success == False
    assert error_response.error_message == "평가 실패"
    assert error_response.total_score is None

def test_map_analysis_status_to_korean():
    """DB 상태값을 한국어로 변환 테스트"""
    assert map_analysis_status_to_korean("pending") == "대기중"
    assert map_analysis_status_to_korean("processing") == "분석중"
    assert map_analysis_status_to_korean("completed") == "완료"
    assert map_analysis_status_to_korean("failed") == "실패"
    
    # 존재하지 않는 상태는 원래값 반환
    assert map_analysis_status_to_korean("unknown") == "unknown"

def test_map_korean_status_to_analysis():
    """한국어 상태값을 DB 상태값으로 변환 테스트"""
    assert map_korean_status_to_analysis("대기중") == "pending"
    assert map_korean_status_to_analysis("분석중") == "processing"
    assert map_korean_status_to_analysis("완료") == "completed"
    assert map_korean_status_to_analysis("실패") == "failed"
    
    # 존재하지 않는 상태는 원래값 반환
    assert map_korean_status_to_analysis("알수없음") == "알수없음"

def test_evaluation_response_to_db_json():
    """EvaluationResponse를 딕셔너리로 변환 테스트"""
    response = EvaluationResponse(
        success=True,
        total_score=85.5,
        overall_strengths=["강점1", "강점2"]
    )
    
    json_data = evaluation_response_to_db_json(response)
    assert json_data["success"] == True
    assert json_data["total_score"] == 85.5
    assert "overall_strengths" in json_data
    assert len(json_data["overall_strengths"]) == 2

def test_db_json_to_evaluation_response():
    """딕셔너리를 EvaluationResponse로 변환 테스트"""
    json_data = {
        "success": True,
        "total_score": 75.0,
        "overall_weaknesses": ["약점1", "약점2", "약점3"]
    }
    
    response = db_json_to_evaluation_response(json_data)
    assert response.success == True
    assert response.total_score == 75.0
    assert len(response.overall_weaknesses) == 3

def test_get_all_sections():
    """모든 평가 섹션 목록 반환 테스트"""
    sections = get_all_sections()
    assert len(sections) == 7  # 예비창업패키지는 7개 섹션
    assert "1.1. 창업아이템의 개발동기" in sections
    assert "4.1. 대표자 및 팀원의 보유역량" in sections