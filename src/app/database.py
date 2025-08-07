from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from pathlib import Path
import os
import sys

# --------------------
# 🔧 수정된 부분: 환경 변수 로딩 및 검증 로직
# --------------------
def get_db_url() -> str:
    """
    .env 파일에서 데이터베이스 연결 정보를 읽어 URL을 생성합니다.
    필수 환경 변수가 누락된 경우 오류를 발생시킵니다.
    """
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}")
        sys.exit(1)
    
    load_dotenv(dotenv_path=env_path)

    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")

    # 필수 환경 변수 검증
    if not all([db_user, db_pass, db_host, db_port, db_name]):
        print("Error: Missing one or more required database environment variables.")
        print("Please check your .env file and ensure DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME are all set.")
        sys.exit(1)

    return f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

# DATABASE_URL을 동적으로 생성
DATABASE_URL = get_db_url()

# SQLAlchemy 엔진 & 세션 설정
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 모델 클래스 (ORM 모델에서 상속)
Base = declarative_base()

# --------------------
# 🔧 수정된 부분: DB 세션 의존성 주입 함수
# --------------------
def get_db():
    """
    FastAPI 의존성 주입을 위한 DB 세션 제너레이터.
    try-finally 구문을 사용하여 세션이 항상 닫히도록 보장합니다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()