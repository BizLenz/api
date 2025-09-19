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
    Enum,
    desc,
    CheckConstraint,
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

    id = Column(
        String(255), primary_key=True, comment="Cognito Sub (서비스 내부 고유 ID)"
    )
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="서비스 프로필 생성 일시",
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="프로필 수정 일시",
    )

    __table_args__ = (Index("idx_users_created_at", "created_at"),)

    business_plans = relationship(
        "BusinessPlan", back_populates="user", cascade="all, delete-orphan"
    )


# -----------------------
# BusinessPlans 테이블
# -----------------------
class BusinessPlan(Base):
    __tablename__ = "business_plans"

    id = Column(
        Integer, primary_key=True, autoincrement=True, comment="사업계획서 고유 ID"
    )
    user_id = Column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="업로더 사용자",
    )
    file_name = Column(String(255), nullable=False, comment="원본 파일명")
    file_path = Column(String(500), nullable=False, comment="스토리지 내 저장 경로")
    file_size = Column(BigInteger, comment="바이트 단위 파일 크기")
    mime_type = Column(String(100), comment="파일 MIME 타입")
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), comment="업로드 시각"
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="수정 시각",
    )

    status = Column(
        String(20),
        server_default="pending",
        nullable=False,
        comment="분석 상태 (pending, processing, completed, failed)",
    )

    latest_job_id = Column(
        Integer,
        ForeignKey("analysis_jobs.id", ondelete="SET NULL"),
        comment="가장 최근 분석 작업 ID",
    )

    __table_args__ = (
        Index("idx_business_plans_user_created", "user_id", desc("created_at")),
        Index("idx_business_plans_user_status", "user_id", "status"),
        Index("idx_business_plans_filename_search", "file_name"),
        Index("idx_business_plans_user_id", "user_id"),
        Index("idx_business_plans_status", "status"),
        Index("idx_business_plans_latest_job", "latest_job_id"),
        Index("idx_business_plans_created_at", "created_at"),
        Index("idx_business_plans_status_updated", "status", desc("updated_at")),
        CheckConstraint("file_size >= 0", name="ck_business_plans_file_size_positive"),
        CheckConstraint(
            "status IN ('pending','processing','completed','failed')",
            name="ck_business_plans_status_valid",
        ),
    )

    user = relationship("User", back_populates="business_plans")
    analysis_jobs = relationship(
        "AnalysisJob",
        back_populates="business_plan",
        cascade="all, delete-orphan",
        foreign_keys="AnalysisJob.plan_id",
    )
    latest_job = relationship(
        "AnalysisJob", foreign_keys=[latest_job_id], post_update=True
    )


# -----------------------
# AnalysisJobs 테이블
# -----------------------
class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(
        Integer, primary_key=True, autoincrement=True, comment="분석 작업 고유 ID"
    )
    plan_id = Column(
        Integer,
        ForeignKey("business_plans.id", ondelete="CASCADE"),
        nullable=False,
        comment="분석 대상 사업계획서",
    )
    job_type = Column(
        String(50), nullable=False, comment="분석 유형 (basic, market, industry 등)"
    )
    status = Column(
        String(20),
        nullable=False,
        comment="작업 상태 (pending, processing, completed, failed)",
    )
    token_usage = Column(Integer, comment="이 작업에서 사용된 토큰 양")
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="작업 생성(요청) 시각",
    )

    gemini_request_id = Column(String(100), comment="Gemini API 요청 ID")
    processing_time_seconds = Column(Integer, comment="처리 시간 (초)")
    error_message = Column(Text, comment="오류 메시지")
    retry_count = Column(
        Integer, server_default="0", nullable=False, comment="재시도 횟수"
    )
    completed_at = Column(TIMESTAMP(timezone=True), comment="완료 시간")

    s3_bucket = Column(String(255), comment="S3 버킷명")
    s3_key = Column(String(500), comment="S3 객체 키")
    s3_region = Column(String(50), server_default="ap-northeast-2", comment="S3 리전")
    upload_status = Column(
        Enum("pending", "uploading", "completed", "failed", name="upload_status_enum"),
        server_default="pending",
        nullable=False,
        comment="S3 업로드 상태",
    )

    __table_args__ = (
        Index(
            "idx_analysis_jobs_plan_type_latest",
            "plan_id",
            "job_type",
            desc("created_at"),
        ),
        Index(
            "idx_analysis_jobs_type_completed",
            "job_type",
            "status",
            desc("completed_at"),
        ),
        Index("idx_analysis_jobs_plan_id", "plan_id"),
        Index("idx_analysis_jobs_status", "status"),
        Index("idx_analysis_jobs_job_type", "job_type"),
        Index("idx_analysis_jobs_created_at", "created_at"),
        Index("idx_analysis_jobs_completed_at", "completed_at"),
        Index("idx_analysis_jobs_plan_status", "plan_id", "status"),
        Index("idx_analysis_jobs_status_created", "status", desc("created_at")),
        Index("idx_analysis_jobs_type_status", "job_type", "status"),
        Index("idx_analysis_jobs_gemini_request", "gemini_request_id"),
        Index("idx_analysis_jobs_s3_bucket_key", "s3_bucket", "s3_key"),
        Index("idx_analysis_jobs_upload_status", "upload_status"),
        CheckConstraint(
            "token_usage >= 0", name="ck_analysis_jobs_token_usage_positive"
        ),
        CheckConstraint(
            "retry_count >= 0", name="ck_analysis_jobs_retry_count_positive"
        ),
        CheckConstraint(
            "processing_time_seconds >= 0",
            name="ck_analysis_jobs_processing_time_positive",
        ),
        CheckConstraint(
            "status IN ('pending','processing','completed','failed')",
            name="ck_analysis_jobs_status_valid",
        ),
    )

    business_plan = relationship(
        "BusinessPlan", back_populates="analysis_jobs", foreign_keys=[plan_id]
    )
    analysis_results = relationship(
        "AnalysisResult", back_populates="analysis_job", cascade="all, delete-orphan"
    )


# -----------------------
# AnalysisResults 테이블
# -----------------------
class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(
        Integer, primary_key=True, autoincrement=True, comment="결과 항목 고유 ID"
    )
    analysis_job_id = Column(
        Integer,
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        comment="이 결과를 생성한 분석 작업",
    )
    evaluation_type = Column(
        String(50),
        nullable=False,
        comment="평가 유형 (overall, market, industry, feedback 등)",
    )
    score = Column(Numeric(5, 2), comment="점수 (0.00–100.00)")
    summary = Column(Text, comment="요약")
    details = Column(JSONB, comment="분석 상세 데이터(JSONB)")
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), comment="생성 일시"
    )

    __table_args__ = (
        Index("idx_analysis_results_job_type", "analysis_job_id", "evaluation_type"),
        Index("idx_analysis_results_type_score", "evaluation_type", desc("score")),
        Index("idx_analysis_results_job_score", "analysis_job_id", desc("score")),
        Index("idx_analysis_results_job_id", "analysis_job_id"),
        Index("idx_analysis_results_type", "evaluation_type"),
        Index("idx_analysis_results_score", "score"),
        Index("idx_analysis_results_created_at", "created_at"),
        Index("idx_analysis_results_details_gin", "details", postgresql_using="gin"),
    )

    analysis_job = relationship("AnalysisJob", back_populates="analysis_results")


# =======================================
# 시장/경쟁사/제품 분석 테이블
# =======================================
class MarketAnalysis(Base):
    __tablename__ = "market_analysis"

    id = Column(
        Integer, primary_key=True, autoincrement=True, comment="분석 데이터 고유 ID"
    )
    market_name = Column(String(255), nullable=False, comment="분석 대상 시장의 이름")
    year = Column(Integer, nullable=False, comment="데이터 기준 연도")
    total_revenue = Column(Numeric(20, 2), comment="전체 시장 매출액")
    cagr = Column(Numeric(5, 2), comment="연평균 성장률 (%)")
    growth_drivers = Column(Text, comment="시장 성장 동인")
    customer_group = Column(String(100), comment="주요 고객군")
    avg_purchase_value = Column(Numeric(15, 2), comment="평균 구매 금액")
    nps = Column(Numeric(5, 2), comment="순추천지수")
    retention_rate = Column(Numeric(5, 2), comment="고객 유지율")
    source = Column(String(255), comment="데이터의 출처")
    last_updated = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="마지막 업데이트 시간",
    )
    industry_trends = Column(JSONB, comment="업종 트렌드 데이터")
    market_conditions = Column(JSONB, comment="시장 상황 데이터")

    __table_args__ = (
        Index("idx_market_analysis_market_year", "market_name", desc("year")),
        Index(
            "idx_market_analysis_trends_gin", "industry_trends", postgresql_using="gin"
        ),
        Index(
            "idx_market_analysis_conditions_gin",
            "market_conditions",
            postgresql_using="gin",
        ),
        Index("idx_market_analysis_revenue_desc", desc("total_revenue")),
        Index("idx_market_analysis_updated", desc("last_updated")),
    )


class CompetitorAnalysis(Base):
    __tablename__ = "competitor_analysis"

    id = Column(
        Integer, primary_key=True, autoincrement=True, comment="분석 데이터 고유 ID"
    )
    market_name = Column(String(255), nullable=False, comment="분석 대상 시장의 이름")
    year = Column(Integer, nullable=False, comment="데이터 기준 연도")
    competitor_name = Column(String(255), nullable=False, comment="경쟁사 이름")
    revenue = Column(Numeric(20, 2), comment="연간 매출액")
    operating_profit = Column(Numeric(20, 2), comment="연간 영업이익")
    debt_ratio = Column(Numeric(10, 2), comment="부채 비율")
    share_percentage = Column(Numeric(5, 2), comment="시장 점유율")
    competitive_advantage = Column(Text, comment="경쟁 우위 요소")
    source = Column(String(255), comment="데이터 출처")
    last_updated = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="마지막 업데이트 시간",
    )

    __table_args__ = (
        Index("idx_competitor_analysis_market_year", "market_name", desc("year")),
        Index("idx_competitor_analysis_competitor", "competitor_name"),
        Index("idx_competitor_analysis_share_desc", desc("share_percentage")),
        Index("idx_competitor_analysis_revenue_desc", desc("revenue")),
    )


class ProductAnalysis(Base):
    __tablename__ = "product_analysis"

    id = Column(
        Integer, primary_key=True, autoincrement=True, comment="분석 데이터 고유 ID"
    )
    competitor_name = Column(String(255), nullable=False, comment="제품 소유 경쟁사")
    product_name = Column(String(255), nullable=False, comment="제품명")
    category = Column(String(100), comment="제품 카테고리")
    price = Column(Numeric(15, 2), comment="대표 가격")
    price_policy_notes = Column(Text, comment="가격 정책 설명")
    distribution_channels = Column(Text, comment="유통 채널")
    tech_level = Column(String(100), comment="기술 수준")
    features = Column(Text, comment="주요 특징")
    last_updated = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="마지막 업데이트 시간",
    )

    __table_args__ = (
        Index("idx_product_analysis_competitor", "competitor_name"),
        Index("idx_product_analysis_category", "category"),
        Index("idx_product_analysis_price_desc", desc("price")),
        Index("idx_product_analysis_product", "product_name"),
    )
