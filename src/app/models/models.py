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
# Users table
# -----------------------
class User(Base):
    __tablename__ = "users"
    id = Column(
        String(255), primary_key=True, comment="OIDC sub claim (internal unique ID)"
    )
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Profile creation timestamp",
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )  # Last modified

    # Relationship (1:N) — one user can upload multiple business plans
    business_plans = relationship(
        "BusinessPlan", back_populates="user", cascade="all, delete-orphan"
    )


# -----------------------
# BusinessPlans table
# -----------------------
class BusinessPlan(Base):
    __tablename__ = "business_plans"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger)
    mime_type = Column(String(100))
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last modified",
    )

    status = Column(
        String(20),
        server_default="pending",
        nullable=False,
        comment="Analysis status (pending, processing, completed, failed)",
    )

    latest_job_id = Column(
        Integer,
        ForeignKey("analysis_jobs.id", ondelete="SET NULL"),
        comment="Most recent analysis job ID",
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
# AnalysisJobs table
# -----------------------
class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(
        Integer, primary_key=True, autoincrement=True, comment="Unique analysis job ID"
    )
    plan_id = Column(
        Integer,
        ForeignKey("business_plans.id", ondelete="CASCADE"),
        nullable=False,
        comment="Target business plan",
    )
    job_type = Column(
        String(50), nullable=False, comment="Analysis type (basic, market, industry, etc.)"
    )
    status = Column(
        String(20),
        nullable=False,
        comment="Job status (pending, processing, completed, failed)",
    )
    token_usage = Column(Integer, comment="Token count used in this job")
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Job creation timestamp",
    )

    gemini_request_id = Column(String(100), comment="Gemini API request ID")
    processing_time_seconds = Column(Integer, comment="Processing time (seconds)")
    error_message = Column(Text, comment="Error message")
    retry_count = Column(
        Integer, server_default="0", nullable=False, comment="Retry count"
    )
    completed_at = Column(TIMESTAMP(timezone=True), comment="Completion timestamp")

    s3_bucket = Column(String(255), comment="S3 bucket name")
    s3_key = Column(String(500), comment="S3 object key")
    s3_region = Column(String(50), server_default="ap-northeast-2", comment="S3 region")
    upload_status = Column(
        Enum("pending", "uploading", "completed", "failed", name="upload_status_enum"),
        server_default="pending",
        nullable=False,
        comment="S3 upload status",
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
# AnalysisResults table
# -----------------------
class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(
        Integer, primary_key=True, autoincrement=True, comment="Unique result ID"
    )
    analysis_job_id = Column(
        Integer,
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        comment="Analysis job that generated this result",
    )
    evaluation_type = Column(
        String(50),
        nullable=False,
        comment="Evaluation type (overall, market, industry, feedback, etc.)",
    )
    score = Column(Numeric(5, 2), comment="Score (0.00–100.00)")
    summary = Column(Text, comment="Summary")
    details = Column(JSONB, comment="Detailed analysis data (JSONB)")
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), comment="Creation timestamp"
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
# Market / Competitor / Product analysis tables
# =======================================
class MarketAnalysis(Base):
    __tablename__ = "market_analysis"

    id = Column(
        Integer, primary_key=True, autoincrement=True, comment="Unique analysis data ID"
    )
    market_name = Column(String(255), nullable=False, comment="Name of the target market")
    year = Column(Integer, nullable=False, comment="Data reference year")
    total_revenue = Column(Numeric(20, 2), comment="Total market revenue")
    cagr = Column(Numeric(5, 2), comment="CAGR (%)")
    growth_drivers = Column(Text, comment="Market growth drivers")
    customer_group = Column(String(100), comment="Primary customer segment")
    avg_purchase_value = Column(Numeric(15, 2), comment="Average purchase value")
    nps = Column(Numeric(5, 2), comment="Net Promoter Score (NPS)")
    retention_rate = Column(Numeric(5, 2), comment="Customer retention rate")
    source = Column(String(255), comment="Data source")
    last_updated = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last updated timestamp",
    )
    industry_trends = Column(JSONB, comment="Industry trend data")
    market_conditions = Column(JSONB, comment="Market conditions data")

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
        Integer, primary_key=True, autoincrement=True, comment="Unique analysis data ID"
    )
    market_name = Column(String(255), nullable=False, comment="Name of the target market")
    year = Column(Integer, nullable=False, comment="Data reference year")
    competitor_name = Column(String(255), nullable=False, comment="Competitor name")
    revenue = Column(Numeric(20, 2), comment="Annual revenue")
    operating_profit = Column(Numeric(20, 2), comment="Annual operating profit")
    debt_ratio = Column(Numeric(10, 2), comment="Debt ratio")
    share_percentage = Column(Numeric(5, 2), comment="Market share (%)")
    competitive_advantage = Column(Text, comment="Competitive advantage")
    source = Column(String(255), comment="Data source")
    last_updated = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last updated timestamp",
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
        Integer, primary_key=True, autoincrement=True, comment="Unique analysis data ID"
    )
    competitor_name = Column(String(255), nullable=False, comment="Competitor owning this product")
    product_name = Column(String(255), nullable=False, comment="Product name")
    category = Column(String(100), comment="Product category")
    price = Column(Numeric(15, 2), comment="Representative price")
    price_policy_notes = Column(Text, comment="Pricing policy notes")
    distribution_channels = Column(Text, comment="Distribution channels")
    tech_level = Column(String(100), comment="Technology level")
    features = Column(Text, comment="Key features")
    last_updated = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last updated timestamp",
    )

    __table_args__ = (
        Index("idx_product_analysis_competitor", "competitor_name"),
        Index("idx_product_analysis_category", "category"),
        Index("idx_product_analysis_price_desc", desc("price")),
        Index("idx_product_analysis_product", "product_name"),
    )
