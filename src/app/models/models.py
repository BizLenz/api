from sqlalchemy import Column, Integer, String, Text, ForeignKey, BigInteger, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), unique=True)
    phone_number = Column(String(20))
    address = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # 관계 (1:N)
    business_plans = relationship("BusinessPlan", back_populates="user", cascade="all, delete")


class BusinessPlan(Base):
    __tablename__ = "business_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger)
    mime_type = Column(String(100))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # 관계 (1:N)
    user = relationship("User", back_populates="business_plans")
    analyses = relationship("Analysis", back_populates="business_plan", cascade="all, delete")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("business_plans.id", ondelete="CASCADE"))
    evaluation_report = Column(JSONB)
    industry_data = Column(JSONB)
    sources = Column(ARRAY(Text))
    feedback = Column(ARRAY(Text))
    bmc = Column(JSONB)
    visualization_path = Column(String(500))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # 관계
    business_plan = relationship("BusinessPlan", back_populates="analyses")
