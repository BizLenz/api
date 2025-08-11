import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

def get_db_url() -> str:
    """
    .env 파일에서 데이터베이스 연결 정보를 읽어 URL을 생성합니다.
    CI 환경에서는 기본값을 사용합니다.
    """
    # CI 환경 감지
    is_ci = os.getenv("CI") or os.getenv("GITHUB_ACTIONS")
    
    if is_ci:
        # CI 환경에서는 SQLite 메모리 DB 사용
        return "sqlite:///:memory:"
    
    # 로컬 환경에서는 .env 파일 사용
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        print(f"Warning: .env file not found at {env_path}")
        # 테스트 환경을 위한 기본값
        return "sqlite:///:memory:"

    db_user = settings.db_user
    db_pass = settings.db_password
    db_host = settings.db_host
    db_port = settings.db_port
    db_name = settings.db_name

    # 필수 환경 변수 검증
    if not all([db_user, db_pass, db_host, db_port, db_name]):
        if os.getenv("ENV") == "production":
            raise RuntimeError("Missing required database environment variables")
        print("Warning: Missing database environment variables, using SQLite for testing")
        return "sqlite:///:memory:"
    
    # URL 파싱 오류 방지를 위한 인코딩 (내장 함수 사용)
    encoded_user = str(db_user).replace('@', '%40').replace(':', '%3A').replace('/', '%2F')
    encoded_pass = str(db_pass).replace('@', '%40').replace(':', '%3A').replace('/', '%2F')
    
    return f"postgresql://{encoded_user}:{encoded_pass}@{db_host}:{db_port}/{db_name}"

# 데이터베이스 URL 생성
DATABASE_URL = get_db_url()

# SQLAlchemy 엔진 생성
if DATABASE_URL.startswith("sqlite"):
    # SQLite의 경우
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL의 경우
    engine = create_engine(DATABASE_URL)

# 세션 로컬 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 생성
Base = declarative_base()

def get_db():
    """데이터베이스 세션을 생성하고 반환합니다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()