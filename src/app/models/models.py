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
    Enum
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
# Analyses 테이블 (Gemini + S3 통합)
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
    
    # ===================
    # Gemini 연동 필드들 (11개)
    # ===================
    
    # Gemini API 요청 관리
    gemini_request_id = Column(String(100), nullable=True, comment="Gemini API 요청 고유 ID")
    gemini_model_version = Column(String(50), nullable=True, comment="사용된 Gemini 모델 버전")
    
    # 토큰 사용량 추적
    prompt_tokens = Column(Integer, nullable=True, comment="프롬프트 토큰 수")
    completion_tokens = Column(Integer, nullable=True, comment="완성 토큰 수") 
    total_tokens = Column(Integer, nullable=True, comment="총 토큰 수")
    
    # API 응답 메타데이터
    gemini_response_time = Column(Integer, nullable=True, comment="API 응답 시간(ms)")
    gemini_response_metadata = Column(JSONB, nullable=True, comment="Gemini API 응답 메타데이터")
    
    # 분석 상태 및 오류 처리
    status = Column(Enum('pending', 'processing', 'completed', 'failed', name='analysis_status_enum'), 
                   default='pending', comment="분석 상태")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="분석 완료 시간")
    error_message = Column(Text, nullable=True, comment="오류 메시지")
    retry_count = Column(Integer, default=0, comment="재시도 횟수")
    
    # ===================
    # S3 연동 필드들 (16개)
    # ===================
    
    # S3 저장소 관련 필드
    s3_bucket = Column(String(255), nullable=True, comment="S3 버킷명")
    s3_key = Column(String(500), nullable=True, comment="S3 객체 키 (파일 경로)")
    s3_region = Column(String(50), nullable=True, server_default='ap-northeast-2', comment="S3 리전")
    
    # 파일 메타데이터 필드
    file_size = Column(BigInteger, nullable=True, comment="파일 크기 (bytes)")
    file_checksum = Column(String(64), nullable=True, comment="파일 체크섬 (SHA256)")
    content_type = Column(String(100), nullable=True, comment="파일 MIME 타입")
    
    # 업로드 상태 관리 필드
    upload_status = Column(Enum('pending', 'uploading', 'completed', 'failed', name='upload_status_enum'),
                          server_default='pending', comment="S3 업로드 상태")
    upload_started_at = Column(DateTime(timezone=True), nullable=True, comment="업로드 시작 시간")
    upload_completed_at = Column(DateTime(timezone=True), nullable=True, comment="업로드 완료 시간")
    
    # S3 접근 관리 필드
    presigned_url_expires_at = Column(DateTime(timezone=True), nullable=True, comment="프리사인드 URL 만료 시간")
    download_count = Column(Integer, server_default='0', comment="다운로드 횟수")
    last_accessed_at = Column(DateTime(timezone=True), nullable=True, comment="마지막 접근 시간")
    
    # 백업 및 버전 관리 필드
    backup_s3_key = Column(String(500), nullable=True, comment="백업 S3 키")
    version_id = Column(String(100), nullable=True, comment="S3 객체 버전 ID")
    is_archived = Column(Boolean, server_default='false', comment="아카이브 여부")
    archive_date = Column(DateTime(timezone=True), nullable=True, comment="아카이브 날짜")
    
    # 관계
    business_plan = relationship("BusinessPlan", back_populates="analyses")