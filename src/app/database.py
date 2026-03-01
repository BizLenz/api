import logging
import os
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_db_url() -> str:
    """
    Determine the database URL

    - CI / test environments use SQLite in-memory
    - Local dev reads from .env (PostgreSQL)
    - Falls back to SQLite if .env is missing or DB vars are incomplete
    """
    is_test = (
        os.getenv("CI")
        or os.getenv("GITHUB_ACTIONS")
        or os.getenv("PYTEST_CURRENT_TEST")
    )
    if is_test:
        return "sqlite:///:memory:"

    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        logger.warning("Warning: .env file not found at %s, using SQLite", env_path)
        return "sqlite:///:memory:"

    db_user = settings.db_user
    db_pass = settings.db_password
    db_host = settings.db_host
    db_port = settings.db_port
    db_name = settings.db_name

    if not all([db_user, db_pass, db_host, db_port, db_name]):
        if os.getenv("ENVIRONMENT") == "production":
            raise RuntimeError("Missing required database environment variables")
        logger.warning("Incomplete DB config, using SQLite")
        return "sqlite:///:memory:"

    safe_user = quote_plus(db_user)
    safe_pass = quote_plus(db_pass)
    return f"postgresql://{safe_user}:{safe_pass}@{db_host}:{db_port}/{db_name}"


DATABASE_URL = get_db_url()

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
