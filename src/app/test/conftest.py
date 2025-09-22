# src/app/test/conftest.py
import os
import pytest
from httpx import AsyncClient, ASGITransport
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("S3_BUCKET", "test-bucket")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def app_instance():
    from app.main import app

    return app


@pytest.fixture
async def client(app_instance):
    async with AsyncClient(
        transport=ASGITransport(app=app_instance), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture(autouse=True, scope="session")
def mock_secret_prompts(monkeypatch):
    """
    Auto-mock the secret pre_startup module for ALL tests.
    This runs before any test and patches the import at module level.
    """

    # Define comprehensive mock data for 예비창업패키지 evaluation
    class MockPreStartupModule:
        """Mock implementation of pre_startup module"""

        SYSTEM_PROMPT = """You are an evaluation assistant for 예비창업패키지 (Pre-Startup Package) program.

Evaluation Focus:
- Market potential and customer problem validation (30%)
- Technical innovation and feasibility (30%) 
- Execution plan and team capability (20%)
- Initial funding needs and financial planning (20%)

Provide objective, constructive feedback for early-stage business ideas.
"""

        SECTION_ANALYSIS_PROMPT_TEMPLATE = """
📋 **예비창업패키지 섹션 분석**
분석 대상: {section_name}
최대 점수: {max_score}점 (전체 {max_score}%)
분석 시간: 2025년 예비창업패키지 기준

**📊 평가 기준 (Pillars):**
{pillars_description}

**📝 분석 출력 형식:**
{pillar_scoring_format}

**평가 지침:**
1. 사업계획서 내용을 충실히 반영하여 분석
2. 예비창업 초기 단계(아이디어 검증) 관점에서 평가  
3. 점수는 루브릭 기준 0-{max_score}점 범위로 부여
4. 근거는 사업계획서 내용과 예비창업 기준에 기반
5. 한국어로 명확하고 전문적인 분석 작성

**예비창업 특화 고려사항:**
- 상용화보다는 아이디어 검증과 초기 실행 가능성 중점
- 기술혁신성과 시장성의 조화성 평가
- 최소 실행 자금(MVP 개발 등) 현실성 검토
- 팀 역량과 초기 실행 계획의 구체성 평가
        """

        FINAL_REPORT_PROMPT = """
👑 **예비창업패키지 종합 평가 보고서 생성**

**📋 입력 데이터 (섹션별 분석):**
{structured_analyses_input}

**🎯 평가 기준 (예비창업패키지 2025)**
- 총점: 0-100점 (합산)
- 기술혁신성(30%) + 시장성(30%) + 실행가능성(25%) + 팀/재무(15%)
- 초기 단계 사업: 아이디어 검증과 MVP 실행 가능성 중점

**📊 종합 평가 기준:**
- 85-100점: 최우선 지원 (A등급)
- 70-84점: 우선 지원 (B등급)  
- 55-69점: 보완 후 지원 가능 (C등급)
- 40-54점: 추가 준비 필요 (D등급)
- 0-39점: 현 단계 지원 어려움 (F등급)

**📋 출력 형식 (JSON):**
{{
    "overall_score": "종합점수 (0-100, 소수점 1자리)",
    "grade": "등급 (A/B/C/D/F)", 
    "total_max_score": 100,
    "pre_startup_fit": "적합성 (최우선/우선/검토/보완/부적합)",
    "strengths": ["강점1", "강점2", "강점3", "강점4"],
    "improvements": ["보완사항1", "보완사항2", "보완사항3"],
    "risks": ["주요 위험1", "주요 위험2"],
    "category_scores": {{"서론": 점수, "시장": 점수, "비즈니스": 점수, "재무": 점수}},
    "final_recommendation": "최종 권고 (지원/추가검토/보완/불가)",
    "support_program": "추천 프로그램 (예비창업패키지/창업기초교육/멘토링)",
    "funding_estimate": "초기 자금 추정 (최소/적정/과다)", 
    "market_readiness": "시장 준비도 (초기/성장/성숙)",
    "tech_readiness": "기술 준비도 (아이디어/프로토타입/MVP/최적화)",
    "executive_summary": "한 문장 종합 평가 (50자 이내)"
}}

**🔍 종합 평가 지침:**
1. 각 섹션 분석의 일관성 검토
2. 예비창업 초기 단계 특성 반영 (완성도보다는 잠재력 중점)
3. 지원 프로그램 적합성 현실적 평가
4. 실행 가능한 구체적 보완 제안
5. 기술/시장/실행/재무 간 균형성 검토
6. 초기 자금 소요와 펀딩 가능성 평가

**⚠️ 주의사항:**
- 예비창업패키지는 상용화 완성 사업이 아닌 초기 아이디어 검증 사업
- 과도한 재무 전망이나 완성된 비즈니스 모델은 비현실적일 수 있음
- 팀 역량과 초기 실행 가능성이 성공의 핵심
- 정부 지원 사업의 공공성/사회적 가치도 고려
        """

        # Comprehensive evaluation criteria for 예비창업패키지
        EVALUATION_CRITERIA = [
            {
                "section_name": "사업개요 및 비전 (Executive Summary & Vision)",
                "main_category": "서론",
                "category_max_score": 20,
                "category_min_score": 0,
                "max_score": 20,
                "pillars": {
                    "사업 아이디어 명확성 (10점)": {
                        "description": "창업 아이디어의 명확한 문제 정의와 해결책 제시",
                        "questions": [
                            "해결하고자 하는 고객의 구체적 문제는 무엇인가?",
                            "기존 솔루션 대비 차별화된 해결 방안 제시 여부",
                            "사업 아이디어가 혁신적이고 독창적인가?",
                            "초기 타겟 고객과 시장 세그먼트가 명확한가?",
                            "고유 가치 제안(Value Proposition)이 설득력 있는가?"
                        ]
                    },
                    "창업 비전과 열정 (10점)": {
                        "description": "장기적 비전과 창업자의 실행 의지 및 준비 상태",
                        "questions": [
                            "3-5년 후 사업 성과에 대한 구체적 비전 제시 여부",
                            "창업자의 전문성과 열정이 사업 성공에 적합한가?",
                            "초기 단계 사업으로서 현실적이고 도전적인 목표 설정 여부",
                            "필요 자원(기술/인력/자금)에 대한 인식과 준비 상태",
                            "창업 과정에서의 학습 의지와 적응력"
                        ]
                    }
                }
            },
            {
                "section_name": "시장 및 고객 분석 (Market & Customer Analysis)",
                "main_category": "시장",
                "category_max_score": 30,
                "category_min_score": 0,
                "max_score": 30,
                "pillars": {
                    "시장 기회와 크기 (15점)": {
                        "description": "사업 아이디어가 해결할 시장의 규모와 성장 가능성",
                        "questions": [
                            "TAM(전체 시장), SAM(서비스 가능 시장), SOM(획득 가능 시장) 분석",
                            "해결 문제의 시장 규모와 성장률 수치화",
                            "시장 트렌드와 타이밍이 사업에 유리한가?",
                            "초기 시장 침투 전략이 현실적인가?",
                            "고객의 문제 인식과 해결의 시급성 수준"
                        ]
                    },
                    "고객 이해와 검증 (15점)": {
                        "description": "타겟 고객의 특성과 문제에 대한 깊은 이해",
                        "questions": [
                            "타겟 고객 페르소나(Persona)가 구체적이고 현실적인가?",
                            "고객의 문제와 니즈에 대한 심층 인터뷰/설문 데이터 제시",
                            "고객의 의사결정 과정과 구매 행동 이해",
                            "초기 고객 확보 전략(Customer Acquisition Strategy) 제시",
                            "MVP(Minimum Viable Product)에 대한 고객 검증 계획"
                        ]
                    }
                }
            },
            {
                "section_name": "비즈니스 모델 및 실행 전략 (Business Model & Execution)",
                "main_category": "비즈니스",
                "category_max_score": 30,
                "category_min_score": 0,
                "max_score": 30,
                "pillars": {
                    "비즈니스 모델 타당성 (15점)": {
                        "description": "수익 창출 방식과 초기 비즈니스 모델의 실행 가능성",
                        "questions": [
                            "주요 수익 경로(Revenue Streams)가 명확하고 현실적인가?",
                            "가치 제공(Value Proposition)과 고객 세그먼트의 일치성",
                            "핵심 자원과 파트너십 전략의 구체성",
                            "비용 구조와 가격 전략의 타당성",
                            "초기 단계 사업으로서 최소 실행 자금(MVP) 소요 추정"
                        ]
                    },
                    "실행 계획과 로드맵 (15점)": {
                        "description": "단계별 실행 계획과 주요 마일스톤 설정",
                        "questions": [
                            "단계별 사업 추진 로드맵이 구체적이고 현실적인가?",
                            "주요 마일스톤과 KPI(Key Performance Indicators) 설정",
                            "필요 기술/인프라 확보 방안과 타임라인",
                            "위험 요인 식별과 대응 전략 제시",
                            "초기 6-12개월 실행 계획의 구체성"
                        ]
                    }
                }
            },
            {
                "section_name": "기술 및 재무 계획 (Technology & Financial Plan)",
                "main_category": "재무",
                "category_max_score": 20,
                "category_min_score": 0,
                "max_score": 20,
                "pillars": {
                    "기술 준비도와 혁신성 (10점)": {
                        "description": "필요 기술의 개발 준비 상태와 혁신성 수준",
                        "questions": [
                            "현재 기술 준비 수준(TRL: Technology Readiness Level)",
                            "핵심 기술의 경쟁력과 차별화 요소",
                            "프로토타입 또는 MVP 개발 상태와 타임라인",
                            "지적재산권(IP) 전략과 보호 방안",
                            "기술 개발의 위험도와 대응 전략"
                        ]
                    },
                    "재무 및 자금 계획 (10점)": {
                        "description": "초기 자금 소요와 자금 조달 전략",
                        "questions": [
                            "예비창업 초기 단계에 적합한 자금 소요 추정",
                            "필요 자금의 용도별 상세 내역 제시",
                            "자금 조달 전략(보육, 대출, 투자 등)의 현실성",
                            "초기 1-2년 운영 자금 소요와 현금흐름 분석",
                            "정부 지원 프로그램 활용 계획의 구체성"
                        ]
                    }
                }
            }
        ]

        # Validation to ensure mock data is complete
        def __post_init__(self):
            total_score = sum(criteria["max_score"] for criteria in self.EVALUATION_CRITERIA)
            assert total_score == 100, f"Total score should be 100, got {total_score}"

    # Create instance of mock module
    mock_pre_startup = MockPreStartupModule()

    # Patch at multiple levels to ensure all imports work
    # 1. Patch the actual module in sys.modules
    sys.modules["app.prompts.pre_startup"] = mock_pre_startup

    # 2. Patch the import in evaluation.py
    import app.routers.evaluation as evaluation_module
    monkeypatch.setattr(
        evaluation_module,
        "SYSTEM_PROMPT",
        mock_pre_startup.SYSTEM_PROMPT
    )
    monkeypatch.setattr(
        evaluation_module,
        "SECTION_ANALYSIS_PROMPT_TEMPLATE",
        mock_pre_startup.SECTION_ANALYSIS_PROMPT_TEMPLATE
    )
    monkeypatch.setattr(
        evaluation_module,
        "FINAL_REPORT_PROMPT",
        mock_pre_startup.FINAL_REPORT_PROMPT
    )
    monkeypatch.setattr(
        evaluation_module,
        "EVALUATION_CRITERIA",
        mock_pre_startup.EVALUATION_CRITERIA
    )

    # 3. Patch the import statement itself
    with patch.dict("sys.modules", {"app.prompts.pre_startup": mock_pre_startup}):
        # 4. Patch the specific import path used in evaluation.py
        with patch("app.routers.evaluation.pre_startup", mock_pre_startup):
            # 5. Also patch at the prompts level
            with patch("app.prompts.pre_startup", mock_pre_startup):
                yield mock_pre_startup


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up common test environment"""
    # Mock environment variables
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("S3_BUCKET_NAME", "test-prestartup-evaluation")
    monkeypatch.setenv("AWS_REGION", "ap-northeast-2")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key-for-mocking")
    monkeypatch.setenv("GEMINI_MODEL_ANALYSIS", "gemini-1.5-flash")

    # Mock database dependency
    class MockDBSession:
        def __init__(self):
            self.commit = Mock()
            self.rollback = Mock()
            self.close = Mock()

    monkeypatch.setattr("app.database.get_db", lambda: MockDBSession())

    # Mock boto3 client to avoid real AWS calls
    monkeypatch.setattr("app.routers.evaluation._s3", Mock())

    # Ensure Python path includes src
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


@pytest.fixture(autouse=True)
def mock_external_services():
    """Mock all external service dependencies"""
    with patch("app.routers.evaluation.boto3") as mock_boto3:
        # Mock S3 client
        mock_s3_client = Mock()
        mock_s3_client.download_file = Mock()
        mock_s3_client.head_object = Mock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        mock_boto3.client.return_value = mock_s3_client
        yield mock_s3_client


@pytest.fixture
def mock_gemini_responses():
    """Provide consistent mock responses for Gemini API"""
    section_analysis = """### 사업개요 및 비전 분석

**사업 아이디어 명확성 (8.5/10)**

- **분석:** 사업계획서에서 개발하려는 AI 기반 스마트 헬스케어 솔루션에 대한 설명이 명확합니다. 기존 헬스케어 서비스의 데이터 처리 한계를 극복하기 위한 블록체인 기술 접목 방안이 혁신적입니다. 정신건강 분야의 초기 시장 타겟을 명확히 설정한 점이 강점입니다.

- **근거:** 문제 정의(정신건강 데이터 보안성 부족)가 구체적이고, 타겟 고객(20-30대 직장인)의 니즈를 정확히 파악하였습니다. 기존 솔루션의 프라이버시 침해 문제를 명확히 지적하여 차별화 포인트가 설득력 있습니다. 다만 기술 구현의 구체성이 다소 부족합니다.

**창업 비전과 열정 (8/10)**

- **분석:** 3년 내 100만 사용자 확보와 글로벌 진출 비전이 명확하게 제시되었습니다. 창업자의 의료 AI 연구 경험과 헬스케어 도메인 전문성이 사업 성공 가능성을 높입니다. 창업 과정에서 지속적 학습과 피벗 가능성에 대한 열정도 느껴집니다.

- **근거:** 창업자의 5년 헬스케어 스타트업 경험과 기술 컨설팅 이력이 사업의 전문성을 뒷받침합니다. 초기 자본으로 12개월 MVP 개발 계획이 현실적이며, 정부 지원 프로그램 활용 의지가 강합니다. 다만 장기 비전 실현을 위한 구체적 전략이 보완 필요합니다.

**종합 평가:** 예비창업 초기 단계로서 명확한 문제 해결 방안과 창업자의 전문성을 바탕으로 좋은 출발점을 제시하였습니다. 기술 구현의 구체성을 보완하면 더욱 설득력 있는 사업계획서가 될 것입니다."""

    final_report = '''{
    "overall_score": 82.5,
    "grade": "B",
    "total_max_score": 100,
    "pre_startup_fit": "우선",
    "strengths": [
        "명확한 문제 정의와 차별화된 기술 솔루션 제시",
        "창업자의 헬스케어 도메인 전문성과 실행 경험",
        "현실적인 초기 MVP 개발 및 시장 검증 계획", 
        "정부 지원 프로그램의 적절한 활용 전략"
    ],
    "improvements": [
        "기술 구현의 구체적 로드맵과 개발 리스크 관리 방안 보완",
        "초기 고객 확보 전략과 마케팅 계획의 구체화",
        "경쟁사 분석과 시장 진입 장벽에 대한 깊이 있는 검토",
        "초기 자금 소요의 용도별 상세 계획 제시"
    ],
    "risks": [
        "보건의료 규제와 데이터 보호 관련 법적 리스크",
        "AI 알고리즘의 정확성과 신뢰성 확보의 기술적 도전",
        "초기 사용자 확보의 마케팅 비용과 시간적 제약"
    ],
    "category_scores": {
        "서론": 16.5,
        "시장": 24.0,
        "비즈니스": 23.0,
        "재무": 19.0
    },
    "final_recommendation": "우선 지원",
    "support_program": "예비창업패키지 + 창업기초교육 병행",
    "funding_estimate": "적정",
    "market_readiness": "초기",
    "tech_readiness": "프로토타입", 
    "executive_summary": "헬스케어 AI 분야의 유망한 초기 사업계획서"
}'''

    return {
        "section_analysis": section_analysis,
        "final_report": final_report,
        "criteria_count": 4  # Number of evaluation sections
    }