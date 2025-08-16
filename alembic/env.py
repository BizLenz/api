# alembic/env.py
import sys
from pathlib import Path

# src 폴더를 Python path에 추가
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from alembic import context

# Base와 models는 sys.path.append 이후에 import
from app.database import Base
from app.models import models  # noqa: F401 - models 전체를 import하여 metadata에 등록

# .env 파일 로드
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

# Alembic 설정
config = context.config

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# metadata 설정 - 모든 테이블 정보가 포함됨
target_metadata = Base.metadata

def get_database_url() -> str:
    """환경변수로부터 DATABASE_URL을 생성합니다."""
    
    # 환경변수 읽기 (기본값 포함)
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "postgres")
    
    # DATABASE_URL 생성
    database_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    print(f"데이터베이스 연결: {db_user}@{db_host}:{db_port}/{db_name}")
    
    return database_url

# DATABASE_URL 설정
try:
    DATABASE_URL = get_database_url()
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
except Exception as e:
    print(f"데이터베이스 연결 설정 오류: {e}")
    print(".env 파일을 확인하고 환경변수를 설정해주세요.")
    sys.exit(1)

def run_migrations_offline() -> None:
    """오프라인 모드에서 마이그레이션 실행"""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """온라인 모드에서 마이그레이션 실행"""
    try:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            context.configure(
                connection=connection, 
                target_metadata=target_metadata
            )

            with context.begin_transaction():
                context.run_migrations()
                
    except Exception as e:
        print(f"데이터베이스 연결 실패: {e}")
        print("데이터베이스 서버 상태와 연결 정보를 확인해주세요.")
        raise

# 마이그레이션 실행
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()