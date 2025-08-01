from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    BigInteger,
    TIMESTAMP
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
# Analyses 테이블
# -----------------------
class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)  # 분석 ID
    plan_id = Column(Integer, ForeignKey("business_plans.id", ondelete="CASCADE"))  # 사업계획서 ID
    evaluation_report = Column(JSONB)  # 종합 평가 결과
    industry_data = Column(JSONB)  # 업종/시장 데이터
    sources = Column(ARRAY(Text))  # 자료 출처
    feedback = Column(ARRAY(Text))  # 피드백 (개선점)
    bmc = Column(JSONB)  # 비즈니스 모델 캔버스
    visualization_path = Column(String(500))  # 시각화 자료 경로
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())  # 분석 요청 일시

    # 관계
    business_plan = relationship("BusinessPlan", back_populates="analyses")
