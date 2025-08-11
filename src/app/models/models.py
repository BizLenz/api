from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    BigInteger,
    TIMESTAMP,
    Boolean,
    DateTime,
    Enum,
    Numeric,
    Index,
    desc
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

# -----------------------
# Users 테이블
# -----------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)  # 사용자 ID
    username = Column(String(50), unique=True, nullable=False)  # 사용자명 (UNIQUE)
    password_hash = Column(String(255), nullable=False)  # 해시된 비밀번호
    email = Column(String(255), unique=True)  # 이메일 (UNIQUE)
    phone_number = Column(String(20))  # 연락처
    address = Column(Text)  # 주소
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())  # 생성일시
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )  # 수정일시
    
    # 관계 (1:N) - 한 사용자는 여러 개의 사업계획서를 업로드할 수 있다
    business_plans = relationship(
        "BusinessPlan",
        back_populates="user",
        cascade="all, delete"
    )

# -----------------------
# BusinessPlans 테이블
# -----------------------
class BusinessPlan(Base):
    __tablename__ = "business_plans"
    id = Column(Integer, primary_key=True, index=True)  # 사업계획서 ID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))  # 업로드한 사용자 ID
    file_name = Column(String(255), nullable=False)  # 원본 파일명
    file_path = Column(String(500), nullable=False)  # 파일 저장 경로
    file_size = Column(BigInteger)  # 파일 크기
    mime_type = Column(String(100))  # 파일 MIME 타입
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())  # 업로드 일시
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )  # 수정일시
    
    # 관계
    user = relationship("User", back_populates="business_plans")
    analyses = relationship(
        "Analysis",
        back_populates="business_plan",
        cascade="all, delete"
    )

# -----------------------
# Analyses 테이블 (실제 DB 스키마에 맞춤)
# -----------------------
class Analysis(Base):
    __tablename__ = "analyses"
    
    # 기본 필드
    id = Column(Integer, primary_key=True, index=True)  # 분석 ID
    plan_id = Column(Integer, ForeignKey("business_plans.id", ondelete="CASCADE"))  # 사업계획서 ID
    
    # 기존 분석 결과 필드
    evaluation_report = Column(JSONB)  # 종합 평가 결과
    industry_data = Column(JSONB)  # 업종/시장 데이터
    sources = Column(ARRAY(Text))  # 자료 출처
    feedback = Column(ARRAY(Text))  # 피드백 (개선점)
    bmc = Column(JSONB)  # 비즈니스 모델 캔버스
    visualization_path = Column(String(500))  # 시각화 자료 경로
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())  # 분석 요청 일시
    
    # Gemini 연동 필드들
    status = Column(String(20), nullable=True)  # 분석 상태
    progress = Column(Integer, nullable=True)  # 진행률 (0-100)
    gemini_request_id = Column(String(100), nullable=True)  # API 요청 ID
    token_usage = Column(Integer, nullable=True)  # 총 토큰 사용량
    processing_time_seconds = Column(Integer, nullable=True)  # 처리 시간 (초)
    overall_score = Column(Numeric(5,2), nullable=True)  # 종합 점수 (0.00-100.00)
    raw_analysis_s3_path = Column(String(500), nullable=True)  # 원본 분석 결과 S3 경로
    raw_file_content_s3_path = Column(String(500), nullable=True)  # 원본 파일 S3 경로
    error_message = Column(Text, nullable=True)  # 오류 메시지
    retry_count = Column(Integer, nullable=True)  # 재시도 횟수
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)  # 완료 시간
    
    # S3 연동 필드들
    s3_bucket = Column(String(255), nullable=True, comment="S3 버킷명")
    s3_key = Column(String(500), nullable=True, comment="S3 객체 키 (파일 경로)")
    s3_region = Column(String(50), nullable=True, server_default='ap-northeast-2', comment="S3 리전")
    file_size = Column(BigInteger, nullable=True, comment="파일 크기 (bytes)")
    file_checksum = Column(String(64), nullable=True, comment="파일 체크섬 (SHA256)")
    content_type = Column(String(100), nullable=True, comment="파일 MIME 타입")
    upload_status = Column(Enum('pending', 'uploading', 'completed', 'failed', name='upload_status_enum'),
                          server_default='pending', comment="S3 업로드 상태")
    upload_started_at = Column(DateTime(timezone=True), nullable=True, comment="업로드 시작 시간")
    upload_completed_at = Column(DateTime(timezone=True), nullable=True, comment="업로드 완료 시간")
    presigned_url_expires_at = Column(DateTime(timezone=True), nullable=True, comment="프리사인드 URL 만료 시간")
    download_count = Column(Integer, server_default='0', comment="다운로드 횟수")
    last_accessed_at = Column(DateTime(timezone=True), nullable=True, comment="마지막 접근 시간")
    backup_s3_key = Column(String(500), nullable=True, comment="백업 S3 키")
    version_id = Column(String(100), nullable=True, comment="S3 객체 버전 ID")
    is_archived = Column(Boolean, server_default='false', comment="아카이브 여부")
    archive_date = Column(DateTime(timezone=True), nullable=True, comment="아카이브 날짜")
    
    # 실제 DB에 있는 인덱스들 추가
    __table_args__ = (
        Index('idx_analyses_archived_status', 'is_archived', 'archive_date'),
        Index('idx_analyses_completed_at_desc', desc('completed_at')),
        Index('idx_analyses_created_at_desc', desc('created_at')),
        Index('idx_analyses_download_count_desc', desc('download_count')),
        Index('idx_analyses_file_size_desc', desc('file_size')),
        Index('idx_analyses_gemini_request_id', 'gemini_request_id'),
        Index('idx_analyses_last_accessed_desc', desc('last_accessed_at')),
        Index('idx_analyses_overall_score_desc', desc('overall_score')),
        Index('idx_analyses_plan_id', 'plan_id'),
        Index('idx_analyses_plan_status', 'plan_id', 'status'),
        Index('idx_analyses_presigned_expires', 'presigned_url_expires_at'),
        Index('idx_analyses_retry_count', 'retry_count'),
        Index('idx_analyses_s3_bucket_key', 's3_bucket', 's3_key'),
        Index('idx_analyses_s3_key', 's3_key'),
        Index('idx_analyses_status', 'status'),
        Index('idx_analyses_status_created', 'status', 'created_at'),
        Index('idx_analyses_upload_completed_desc', desc('upload_completed_at')),
        Index('idx_analyses_upload_status', 'upload_status'),
    )
    
    # 관계
    business_plan = relationship("BusinessPlan", back_populates="analyses")

# -----------------------
# Evaluations 테이블 (실제 DB 스키마에 맞춤)
# -----------------------
class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        Index('idx_evaluations_analysis_id', 'analysis_id'),
        Index('idx_evaluations_analysis_type', 'analysis_id', 'evaluation_type'),
        Index('idx_evaluations_created_desc', desc('created_at')),
        Index('idx_evaluations_evaluated_desc', desc('evaluated_at')),
        Index('idx_evaluations_importance', 'importance_level', desc('score')),
        Index('idx_evaluations_score_desc', desc('score')),
        Index('idx_evaluations_status', 'status'),
        Index('idx_evaluations_type', 'evaluation_type'),
        Index('idx_evaluations_type_score', 'evaluation_type', desc('score')),
    )
    
    # 기본 정보 (한글 코멘트 추가)
    id = Column(Integer, primary_key=True, comment="평가 ID")
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, comment="분석 ID (외래키)")
    
    # 평가 분류
    evaluation_type = Column(String(50), nullable=False, comment="평가 유형 (overall, market, financial, technical, risk)")
    evaluation_category = Column(String(100), nullable=True, comment="평가 카테고리 (세부 분류)")
    score = Column(Numeric(5,2), nullable=True, comment="평가 점수 (0.00-100.00)")
    grade = Column(String(10), nullable=True, comment="평가 등급 (A+, A, B+, B, C+, C, D, F)")
    
    # 평가 내용
    title = Column(String(200), nullable=False, comment="평가 제목")
    summary = Column(Text, nullable=True, comment="평가 요약")
    detailed_feedback = Column(Text, nullable=True, comment="상세 피드백")
    strengths = Column(ARRAY(Text), nullable=True, comment="강점 목록")
    weaknesses = Column(ARRAY(Text), nullable=True, comment="약점 목록")
    recommendations = Column(ARRAY(Text), nullable=True, comment="개선 제안사항")
    
    # 메타데이터
    evaluation_criteria = Column(JSONB, nullable=True, comment="평가 기준 정보")
    metrics = Column(JSONB, nullable=True, comment="평가 지표 및 세부 점수")
    benchmark_data = Column(JSONB, nullable=True, comment="벤치마크 데이터")
    
    # 가중치 및 중요도
    weight = Column(Numeric(5,4), nullable=True, server_default='1.0000', comment="평가 가중치 (0.0000-1.0000)")
    importance_level = Column(String(20), nullable=True, server_default='medium', comment="중요도 (critical, high, medium, low)")
    
    # 상태 관리
    status = Column(String(20), nullable=True, server_default='completed', comment="평가 상태 (pending, processing, completed, failed)")
    confidence_score = Column(Numeric(5,2), nullable=True, comment="평가 신뢰도 (0.00-100.00)")
    
    # 평가자 정보
    evaluator_type = Column(String(50), nullable=True, server_default='ai', comment="평가자 유형 (ai, human, hybrid)")
    evaluator_info = Column(JSONB, nullable=True, comment="평가자 상세 정보")
    
    # 시간 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="평가 생성 시간")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="평가 수정 시간")
    evaluated_at = Column(DateTime(timezone=True), nullable=True, comment="평가 완료 시간")
    
    # 버전 관리
    version = Column(Integer, nullable=True, server_default='1', comment="평가 버전")
    parent_evaluation_id = Column(Integer, ForeignKey("evaluations.id", ondelete="SET NULL"), nullable=True, comment="부모 평가 ID (재평가 시 참조)")
    
    # 관계
    analysis = relationship("Analysis")
    parent_evaluation = relationship("Evaluation", remote_side=[id])


# =======================================
# 🆕 시장분석 테이블들 (누락된 모델 추가)
# =======================================

class MarketAnalysis(Base):
    """
    시장의 거시적 정보(규모, 성장성)와 고객/수요 데이터를 종합적으로 관리
    담당 항목: A. 시장 규모 및 성장성, C. 고객 및 수요 데이터
    """
    __tablename__ = "market_analysis"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="분석 데이터 고유 ID")
    market_name = Column(String(255), nullable=False, comment="분석 대상 시장의 이름")
    year = Column(Integer, nullable=False, comment="데이터의 기준 연도")
    total_revenue = Column(Numeric(20, 2), comment="(A) 해당 연도 전체 시장 매출액")
    cagr = Column(Numeric(5, 2), comment="(A) 연평균 성장률 (%)")
    growth_drivers = Column(Text, comment="(A) 시장 성장 동인 (기술 트렌드, 규제 변화 등)")
    customer_group = Column(String(100), comment="(C) 주요 고객군 (연령, 산업, 지역 등)")
    avg_purchase_value = Column(Numeric(15, 2), comment="(C) 평균 구매 금액")
    nps = Column(Numeric(5, 2), comment="(C) 순추천지수 (Net Promoter Score)")
    retention_rate = Column(Numeric(5, 2), comment="(C) 고객 유지율 (%)")
    source = Column(String(255), comment="데이터의 출처 (보고서, 기사 등)")
    last_updated = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now(), comment="이 행(row)이 마지막으로 업데이트된 시간")

    # 인덱스 추가
    __table_args__ = (
        Index('idx_market_analysis_market_year', 'market_name', 'year'),
        Index('idx_market_analysis_year_desc', desc('year')),
        Index('idx_market_analysis_revenue_desc', desc('total_revenue')),
    )


class CompetitorAnalysis(Base):
    """
    특정 시장, 특정 연도의 경쟁사에 대한 모든 정보(재무, 시장 점유율, 정성적 분석)를 종합적으로 관리
    담당 항목: B. 경쟁사 분석 데이터 (B-1, B-2, B-4)
    """
    __tablename__ = "competitor_analysis"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="분석 데이터 고유 ID")
    market_name = Column(String(255), nullable=False, comment="분석 대상 시장의 이름")
    year = Column(Integer, nullable=False, comment="데이터의 기준 연도")
    competitor_name = Column(String(255), nullable=False, comment="경쟁사 이름")
    revenue = Column(Numeric(20, 2), comment="(B-1) 해당 경쟁사의 연간 매출액")
    operating_profit = Column(Numeric(20, 2), comment="(B-1) 해당 경쟁사의 연간 영업이익")
    debt_ratio = Column(Numeric(10, 2), comment="(B-1) 해당 경쟁사의 부채 비율 (%)")
    share_percentage = Column(Numeric(5, 2), comment="(B-2) 해당 시장에서의 점유율 (%)")
    competitive_advantage = Column(Text, comment="(B-4) 경쟁 우위 요소 (특허, 브랜드, 유통망 등)")
    source = Column(String(255), comment="데이터의 출처")
    last_updated = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now(), comment="이 행(row)이 마지막으로 업데이트된 시간")

    # 인덱스 추가
    __table_args__ = (
        Index('idx_competitor_analysis_market_year', 'market_name', 'year'),
        Index('idx_competitor_analysis_competitor', 'competitor_name'),
        Index('idx_competitor_analysis_revenue_desc', desc('revenue')),
        Index('idx_competitor_analysis_share_desc', desc('share_percentage')),
    )


class ProductAnalysis(Base):
    """
    경쟁사의 개별 제품/서비스에 대한 정보(포트폴리오, 가격, 유통)를 종합적으로 관리
    담당 항목: B-3. 제품/서비스 포트폴리오, D. 가격 및 유통 데이터
    """
    __tablename__ = "product_analysis"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="분석 데이터 고유 ID")
    competitor_name = Column(String(255), nullable=False, comment="이 제품을 소유한 경쟁사 이름")
    product_name = Column(String(255), nullable=False, comment="제품 또는 서비스의 이름")
    category = Column(String(100), comment="제품 카테고리")
    price = Column(Numeric(15, 2), comment="(D) 대표 가격 정보")
    price_policy_notes = Column(Text, comment="(D) 가격 정책에 대한 상세 설명")
    distribution_channels = Column(Text, comment="(D) 주요 유통 채널 목록 (콤마로 구분된 텍스트 등)")
    tech_level = Column(String(100), comment="(B-3) 제품의 기술적 수준")
    features = Column(Text, comment="(B-3) 제품의 주요 특징 요약")
    last_updated = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now(), comment="이 행(row)이 마지막으로 업데이트된 시간")

    # 인덱스 추가
    __table_args__ = (
        Index('idx_product_analysis_competitor', 'competitor_name'),
        Index('idx_product_analysis_product', 'product_name'),
        Index('idx_product_analysis_category', 'category'),
        Index('idx_product_analysis_price_desc', desc('price')),
    )