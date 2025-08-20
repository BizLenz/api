from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    BigInteger,
    TIMESTAMP,
    Numeric,
    Index,
    Boolean,
    DateTime,
    Enum,
    desc
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

# -----------------------
# Users 테이블 (Cognito 기반 서비스 프로필)
# -----------------------
class User(Base):
    __tablename__ = "users"
    
    # Cognito 기반 서비스 프로필 테이블
    id = Column(Integer, primary_key=True, autoincrement=True, comment="서비스 내부에서 사용하는 고유 ID")
    cognito_sub = Column(String(255), unique=True, nullable=False, comment="Cognito 사용자 고유 식별자 (JWT sub)")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="서비스 프로필 생성 일시")
    updated_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="프로필 수정 일시"
    )
    
    # 토큰 관리 필드
    total_token_usage = Column(Integer, server_default='0', comment="누적 토큰 사용량")
    
    # 서비스 프로필 필드 (선택적)
    display_name = Column(String(100), comment="표시 이름 (선택)")
    last_login_at = Column(TIMESTAMP(timezone=True), comment="마지막 로그인 시간")
    
    # 인덱스 - JWT 검증 및 사용자 관리 최적화
    __table_args__ = (
        Index('idx_users_cognito_sub', 'cognito_sub'),  # 🔥 JWT 검증용 - 최고 우선순위
        Index('idx_users_token_usage', 'total_token_usage'),  # 토큰 사용량 조회
        Index('idx_users_last_login', 'last_login_at'),  # 활성 사용자 분석
        Index('idx_users_created_at', 'created_at'),
    )
    
    # 관계 (1:N)
    business_plans = relationship(
        "BusinessPlan",
        back_populates="user",
        cascade="all, delete-orphan"
    )

# -----------------------
# BusinessPlans 테이블 (파일 관리 최적화)
# -----------------------
class BusinessPlan(Base):
    __tablename__ = "business_plans"
    
    # 기본 필드
    id = Column(Integer, primary_key=True, autoincrement=True, comment="사업계획서 고유 ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="업로더 사용자")
    file_name = Column(String(255), nullable=False, comment="원본 파일명")
    file_path = Column(String(500), nullable=False, comment="스토리지 내 저장 경로")
    file_size = Column(BigInteger, comment="바이트 단위 파일 크기")
    mime_type = Column(String(100), comment="파일 MIME 타입")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="업로드 시각")
    updated_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="수정 시각"
    )
    # 🔄 변경: 외래 키로 명시적 지정 및 ondelete 정책 추가
    latest_job_id = Column(
        Integer, 
        ForeignKey("analysis_jobs.id", ondelete="SET NULL"), 
        comment="가장 최근 분석 작업 ID (상태 조회용)"
    )
    
    # 분석 상태 관리 필드 (API에서 상태 조회용)
    status = Column(String(20), server_default='pending', comment="분석 상태 (pending, processing, completed, failed)")
    
    # 🆕 파일 검색 및 정렬을 위한 필드 추가
    is_selected = Column(Boolean, server_default='false', comment="현재 선택된 파일 여부 (PATCH /files/{id}/select)")
    sort_priority = Column(Integer, server_default='0', comment="정렬 우선순위")
    
    # 인덱스 - API 사용 패턴 기반 최적화
    __table_args__ = (
        # 🔥 핵심 API 패턴 최적화
        Index('idx_business_plans_user_created', 'user_id', desc('created_at')),  # 사용자별 최신순 조회 (대시보드)
        Index('idx_business_plans_user_status', 'user_id', 'status'),  # 사용자별 상태 필터링
        Index('idx_business_plans_filename_search', 'file_name'),  # GET /files/search - 파일명 검색
        Index('idx_business_plans_selected', 'user_id', 'is_selected'),  # PATCH /files/{id}/select
        Index('idx_business_plans_sort', 'user_id', 'sort_priority', desc('created_at')),  # PATCH /files/sort
        
        # 기본 조회 패턴
        Index('idx_business_plans_user_id', 'user_id'),
        Index('idx_business_plans_status', 'status'),
        Index('idx_business_plans_latest_job', 'latest_job_id'),
        Index('idx_business_plans_created_at', 'created_at'),
        
        # 복합 조회 최적화
        Index('idx_business_plans_status_updated', 'status', desc('updated_at')),  # 상태별 최신순
    )
    
    # 관계
    user = relationship("User", back_populates="business_plans")
    analysis_jobs = relationship(
        "AnalysisJob",
        back_populates="business_plan",
        cascade="all, delete-orphan",
        foreign_keys="AnalysisJob.plan_id"
    )

# -----------------------
# AnalysisJobs 테이블 (분석 작업 최적화)
# -----------------------
class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    
    # 기본 필드
    id = Column(Integer, primary_key=True, autoincrement=True, comment="분석 작업 고유 ID")
    plan_id = Column(Integer, ForeignKey("business_plans.id", ondelete="CASCADE"), nullable=False, comment="분석 대상 사업계획서")
    job_type = Column(String(50), nullable=False, comment="분석 유형 (basic, market, industry 등)")
    # 🔄 수정: 프론트엔드 기준으로 상태값 통일 (running → processing)
    status = Column(String(20), nullable=False, comment="작업 상태 (pending, processing, completed, failed)")
    token_usage = Column(Integer, comment="이 작업에서 사용된 토큰 양")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="작업 생성(요청) 시각")
    
    # Gemini 연동 필드들
    gemini_request_id = Column(String(100), comment="Gemini API 요청 ID")
    processing_time_seconds = Column(Integer, comment="처리 시간 (초)")
    error_message = Column(Text, comment="오류 메시지")
    retry_count = Column(Integer, server_default='0', comment="재시도 횟수")
    completed_at = Column(TIMESTAMP(timezone=True), comment="완료 시간")
    
    # S3 연동 필드들
    s3_bucket = Column(String(255), comment="S3 버킷명")
    s3_key = Column(String(500), comment="S3 객체 키 (파일 경로)")
    s3_region = Column(String(50), server_default='ap-northeast-2', comment="S3 리전")
    file_checksum = Column(String(64), comment="파일 체크섬 (SHA256)")
    content_type = Column(String(100), comment="파일 MIME 타입")
    upload_status = Column(
        Enum('pending', 'uploading', 'completed', 'failed', name='upload_status_enum'),
        server_default='pending', 
        comment="S3 업로드 상태"
    )
    upload_started_at = Column(DateTime(timezone=True), comment="업로드 시작 시간")
    upload_completed_at = Column(DateTime(timezone=True), comment="업로드 완료 시간")
    presigned_url_expires_at = Column(DateTime(timezone=True), comment="프리사인드 URL 만료 시간")
    download_count = Column(Integer, server_default='0', comment="다운로드 횟수")
    last_accessed_at = Column(DateTime(timezone=True), comment="마지막 접근 시간")
    backup_s3_key = Column(String(500), comment="백업 S3 키")
    version_id = Column(String(100), comment="S3 객체 버전 ID")
    is_archived = Column(Boolean, server_default='false', comment="아카이브 여부")
    archive_date = Column(DateTime(timezone=True), comment="아카이브 날짜")
    raw_analysis_s3_path = Column(String(500), comment="원본 분석 결과 S3 경로")
    raw_file_content_s3_path = Column(String(500), comment="원본 파일 S3 경로")
    
    # 🗑️ 삭제: is_latest 컬럼 제거 (created_at으로 동적 파악)
    
    # 인덱스 - API 사용 패턴 기반 최적화
    __table_args__ = (
        # 🔥 핵심 API 최적화 인덱스 (is_latest 관련 인덱스 제거)
        Index('idx_analysis_jobs_plan_type_latest', 'plan_id', 'job_type', desc('created_at')),  # 파일별 분석유형별 최신
        Index('idx_analysis_jobs_type_completed', 'job_type', 'status', desc('completed_at')),  # 분석유형별 완료된 작업
        
        # 기본 조회 패턴
        Index('idx_analysis_jobs_plan_id', 'plan_id'),
        Index('idx_analysis_jobs_status', 'status'),
        Index('idx_analysis_jobs_job_type', 'job_type'),
        Index('idx_analysis_jobs_created_at', 'created_at'),
        Index('idx_analysis_jobs_completed_at', 'completed_at'),
        
        # 복합 조회 최적화
        Index('idx_analysis_jobs_plan_status', 'plan_id', 'status'),
        Index('idx_analysis_jobs_status_created', 'status', desc('created_at')),
        Index('idx_analysis_jobs_type_status', 'job_type', 'status'),
        
        # Gemini & S3 관련
        Index('idx_analysis_jobs_gemini_request', 'gemini_request_id'),
        Index('idx_analysis_jobs_s3_bucket_key', 's3_bucket', 's3_key'),
        Index('idx_analysis_jobs_upload_status', 'upload_status'),
        Index('idx_analysis_jobs_archived', 'is_archived', 'archive_date'),
    )
    
    # 관계
    business_plan = relationship(
        "BusinessPlan",
        back_populates="analysis_jobs",
        foreign_keys=[plan_id]
    )
    analysis_results = relationship(
        "AnalysisResult",
        back_populates="analysis_job",
        cascade="all, delete-orphan"
    )

# -----------------------
# AnalysisResults 테이블 (분석 결과 조회 최적화 - 대폭 단순화)
# -----------------------
class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    # 기본 필드
    id = Column(Integer, primary_key=True, autoincrement=True, comment="결과 항목 고유 ID")
    analysis_job_id = Column(Integer, ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False, comment="이 결과를 생성한 분석 작업")
    evaluation_type = Column(String(50), nullable=False, comment="평가 유형 (overall, market, industry, feedback 등)")
    score = Column(Numeric(5,2), comment="점수 (0.00–100.00)")
    summary = Column(Text, comment="요약")
    details = Column(JSONB, comment="분석 유형별 특화 데이터 저장소 (모든 상세 평가 데이터 통합)")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성 일시")
    

    
    # 인덱스 - API 응답 최적화 (단순화된 구조에 맞춰 조정)
    __table_args__ = (
        # 🔥 핵심 API 최적화 인덱스
        Index('idx_analysis_results_job_type', 'analysis_job_id', 'evaluation_type'),  # 분석작업별 평가유형 조회
        Index('idx_analysis_results_type_score', 'evaluation_type', desc('score')),  # 평가유형별 점수 랭킹
        Index('idx_analysis_results_job_score', 'analysis_job_id', desc('score')),  # 분석작업별 점수 순위
        
        # 기본 조회 패턴
        Index('idx_analysis_results_job_id', 'analysis_job_id'),
        Index('idx_analysis_results_type', 'evaluation_type'),
        Index('idx_analysis_results_score', 'score'),
        Index('idx_analysis_results_created_at', 'created_at'),
        
        # JSONB 검색 최적화 (PostgreSQL GIN 인덱스)
        Index('idx_analysis_results_details_gin', 'details', postgresql_using='gin'),
    )
    
    # 관계
    analysis_job = relationship("AnalysisJob", back_populates="analysis_results")

# =======================================
# 시장분석 테이블들 (industry-data API 최적화)
# =======================================

class MarketAnalysis(Base):
    """
    GET /api/analysis/industry-data API 최적화
    시장의 거시적 정보(규모, 성장성)와 고객/수요 데이터를 종합적으로 관리
    """
    __tablename__ = "market_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="분석 데이터 고유 ID")
    market_name = Column(String(255), nullable=False, comment="분석 대상 시장의 이름")
    year = Column(Integer, nullable=False, comment="데이터의 기준 연도")
    total_revenue = Column(Numeric(20, 2), comment="(A) 해당 연도 전체 시장 매출액")
    cagr = Column(Numeric(5, 2), comment="(A) 연평균 성장률 (%)")
    growth_drivers = Column(Text, comment="(A) 시장 성장 동인")
    customer_group = Column(String(100), comment="(C) 주요 고객군")
    avg_purchase_value = Column(Numeric(15, 2), comment="(C) 평균 구매 금액")
    nps = Column(Numeric(5, 2), comment="(C) 순추천지수")
    retention_rate = Column(Numeric(5, 2), comment="(C) 고객 유지율")
    source = Column(String(255), comment="데이터의 출처")
    last_updated = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), comment="마지막 업데이트 시간")
    
    # 🆕 API 응답용 추가 필드
    industry_trends = Column(JSONB, comment="업종 트렌드 데이터")
    market_conditions = Column(JSONB, comment="시장 상황 데이터")

    # 인덱스 - industry-data API 최적화
    __table_args__ = (
        Index('idx_market_analysis_market_year', 'market_name', desc('year')),  # 시장별 최신 연도 우선
        Index('idx_market_analysis_trends_gin', 'industry_trends', postgresql_using='gin'),
        Index('idx_market_analysis_conditions_gin', 'market_conditions', postgresql_using='gin'),
        Index('idx_market_analysis_revenue_desc', desc('total_revenue')),
        Index('idx_market_analysis_updated', desc('last_updated')),
    )

class CompetitorAnalysis(Base):
    """경쟁사 분석 데이터"""
    __tablename__ = "competitor_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="분석 데이터 고유 ID")
    market_name = Column(String(255), nullable=False, comment="분석 대상 시장의 이름")
    year = Column(Integer, nullable=False, comment="데이터의 기준 연도")
    competitor_name = Column(String(255), nullable=False, comment="경쟁사 이름")
    revenue = Column(Numeric(20, 2), comment="경쟁사 연간 매출액")
    operating_profit = Column(Numeric(20, 2), comment="경쟁사 연간 영업이익")
    debt_ratio = Column(Numeric(10, 2), comment="경쟁사 부채 비율")
    share_percentage = Column(Numeric(5, 2), comment="시장 점유율")
    competitive_advantage = Column(Text, comment="경쟁 우위 요소")
    source = Column(String(255), comment="데이터의 출처")
    last_updated = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), comment="마지막 업데이트 시간")

    __table_args__ = (
        Index('idx_competitor_analysis_market_year', 'market_name', desc('year')),
        Index('idx_competitor_analysis_competitor', 'competitor_name'),
        Index('idx_competitor_analysis_share_desc', desc('share_percentage')),
        Index('idx_competitor_analysis_revenue_desc', desc('revenue')),
    )

class ProductAnalysis(Base):
    """제품/서비스 분석 데이터"""
    __tablename__ = "product_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="분석 데이터 고유 ID")
    competitor_name = Column(String(255), nullable=False, comment="제품 소유 경쟁사")
    product_name = Column(String(255), nullable=False, comment="제품명")
    category = Column(String(100), comment="제품 카테고리")
    price = Column(Numeric(15, 2), comment="대표 가격")
    price_policy_notes = Column(Text, comment="가격 정책 설명")
    distribution_channels = Column(Text, comment="유통 채널")
    tech_level = Column(String(100), comment="기술적 수준")
    features = Column(Text, comment="주요 특징")
    last_updated = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), comment="마지막 업데이트 시간")

    __table_args__ = (
        Index('idx_product_analysis_competitor', 'competitor_name'),
        Index('idx_product_analysis_category', 'category'),
        Index('idx_product_analysis_price_desc', desc('price')),
        Index('idx_product_analysis_product', 'product_name'),
    )