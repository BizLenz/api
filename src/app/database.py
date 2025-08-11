import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

def get_db_url() -> str:
    """
    Settings 클래스를 사용하여 데이터베이스 연결 URL을 생성합니다.
    CI 환경에서는 SQLite 메모리 DB를 사용합니다.
    """
    # CI 환경 감지
    is_ci = os.getenv("CI") or os.getenv("GITHUB_ACTIONS")
    
    if is_ci:
        # CI 환경에서는 SQLite 메모리 DB 사용
        return "sqlite:///:memory:"
    
    # 로컬 환경에서는 settings 클래스 사용
    try:
        from .settings import settings
        
        # settings에서 DB 정보 가져오기
        return f"postgresql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        
    except ImportError:
        # settings 클래스를 import할 수 없는 경우 (예: 테스트 환경)
        print("Warning: Cannot import settings, using SQLite for testing")
        return "sqlite:///:memory:"
    except Exception as e:
        # settings에서 DB 정보를 가져올 수 없는 경우
        print(f"Warning: Error loading database settings ({e}), using SQLite for testing")
        return "sqlite:///:memory:"

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

# 설정 정보 출력 함수 (디버깅용)
def print_db_info():
    """현재 데이터베이스 연결 정보를 출력합니다."""
    try:
        from .settings import settings
        print(f"🔗 데이터베이스 연결 설정 완료: {settings.db_user}@{settings.db_host}:{settings.db_port}/{settings.db_name}")
    except:
        print(f"🔗 데이터베이스 연결: {DATABASE_URL}")

# 연결 정보 출력
print_db_info()