import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from alembic import context

# Base와 models는 sys.path.append 이후에 import
from app.database import Base
from app.models import models  # noqa: F401

# .env 로드
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

# Alembic 설정
config = context.config

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> tuple[str, dict]:
    """환경변수로부터 DATABASE_URL을 생성하고 검증합니다."""
    
    # Docker 테스트 환경 체크
    if os.getenv("TESTING") == "docker":
        return "postgresql://test_user:test123@localhost:5433/bizlenz_test", {
            "type": "postgresql", "host": "localhost", "port": "5433", "db": "bizlenz_test"
        }
    
    # SQLite 테스트 환경
    if os.getenv("TESTING") == "true":
        return "sqlite:///:memory:", {"type": "sqlite", "location": "memory"}
    
    # 기존 PostgreSQL 로직
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "postgres")

    # 필수 환경변수 검증 (실제 값이 있는지 확인)
    if not os.getenv("DB_HOST"):  # 기본값이 아닌 실제 환경변수 확인
        raise ValueError("DB_HOST 환경변수는 반드시 설정해야 합니다")

    # DATABASE_URL 생성
    database_url = (
        f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    )

    # 연결 정보도 함께 반환
    db_info = {"user": db_user, "host": db_host, "port": db_port, "name": db_name}

    return database_url, db_info


# DATABASE_URL 설정
try:
    DATABASE_URL, db_info = get_database_url()
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    
    if os.getenv("TESTING") == "docker":
        print(f"Docker 테스트 환경: PostgreSQL {db_info['host']}:{db_info['port']}/{db_info['db']}")
    elif os.getenv("TESTING") == "true":
        print("테스트 환경: SQLite 메모리 DB 사용")
    else:
        print(
            f"데이터베이스 연결 설정 완료: {db_info['user']}@{db_info['host']}:{db_info['port']}/{db_info['name']}"
        )
except ValueError as e:
    print(f"환경변수 설정 오류: {e}")
    print(".env 파일을 확인하고 필수 환경변수를 설정해주세요.")
    sys.exit(1)
except Exception as e:
    print(f"예상치 못한 오류: {e}")
    sys.exit(1)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    try:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)

            with context.begin_transaction():
                context.run_migrations()

    except Exception as e:
        print(f"데이터베이스 연결 실패: {e}")
        print("데이터베이스 서버 상태와 연결 정보를 확인해주세요.")
        raise


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()