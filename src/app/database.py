import os
from pathlib import Path
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings


def get_db_url() -> str:
    """
    create database url from .env file
    if CI environment, use SQLite memory DB
    """
    # Check if CI environment
    is_ci = os.getenv("CI") or os.getenv("GITHUB_ACTIONS")

    if is_ci:
        return "sqlite:///:memory:"

    # Use .env file in local environment
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        print(f"Warning: .env file not found at {env_path}")
        return "sqlite:///:memory:"

    db_user = settings.db_user
    db_pass = settings.db_password
    db_host = settings.db_host
    db_port = settings.db_port
    db_name = settings.db_name

    if not all([db_user, db_pass, db_host, db_port, db_name]):
        if os.getenv("ENV") == "production":
            raise RuntimeError("Missing required database environment variables")
        print(
            "Warning: Missing database environment variables, using SQLite for testing"
        )
        return "sqlite:///:memory:"

    safe_user = quote_plus(db_user)
    safe_pass = quote_plus(db_pass)

    return f"postgresql://{safe_user}:{safe_pass}@{db_host}:{db_port}/{db_name}"


DATABASE_URL = get_db_url()

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Create and return a database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
