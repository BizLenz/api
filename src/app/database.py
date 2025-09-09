import os
from pathlib import Path
from urllib.parse import quote_plus  # 1. URL 인코딩을 위해 import
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker  # 2. DeclarativeBase import
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
        print(
            "Warning: Missing database environment variables, using SQLite for testing"
        )
        return "sqlite:///:memory:"

    # 1. URL 파싱 오류 방지를 위해 사용자 이름과 비밀번호를 인코딩합니다.
    safe_user = quote_plus(db_user)
    safe_pass = quote_plus(db_pass)

    return f"postgresql://{safe_user}:{safe_pass}@{db_host}:{db_port}/{db_name}"


# 데이터베이스 URL 생성
DATABASE_URL = get_db_url()

# SQLAlchemy 엔진 생성
if DATABASE_URL.startswith("sqlite"):
    # SQLite의 경우
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL의 경우
    engine = create_engine(DATABASE_URL)

# 세션 로컬 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 2. DeclarativeBase를 상속하는 Base 클래스를 생성하는 방식으로 변경합니다.
class Base(DeclarativeBase):
    pass


def get_db():
    """데이터베이스 세션을 생성하고 반환합니다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
