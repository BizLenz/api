import logging
import os
import sys
from logging.config import fileConfig
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from alembic import context  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from sqlalchemy import engine_from_config, pool  # noqa: E402

# Base and models must be imported after sys.path.append
from app.database import Base  # noqa: E402
from app.models import models  # noqa: E402, F401

logger = logging.getLogger("alembic.env")

# Load .env
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

# Alembic configuration
config = context.config

# Logging configuration
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> tuple[str, dict]:
    """Build and validate DATABASE_URL from environment variables."""

    # Check for Docker test environment
    if os.getenv("TESTING") == "docker":
        return "postgresql://test_user:test123@localhost:5433/bizlenz_test", {
            "type": "postgresql",
            "host": "localhost",
            "port": "5433",
            "db": "bizlenz_test",
        }

    # SQLite test environment
    if os.getenv("TESTING") == "true":
        return "sqlite:///:memory:", {"type": "sqlite", "location": "memory"}

    # PostgreSQL
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "postgres")

    # Validate required env vars (ensure actual value is set, not just the default)
    if not os.getenv("DB_HOST"):
        raise ValueError("DB_HOST environment variable must be set")

    # Build DATABASE_URL
    database_url = (
        f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    )

    # Return connection info alongside the URL
    db_info = {"user": db_user, "host": db_host, "port": db_port, "name": db_name}

    return database_url, db_info


# Configure DATABASE_URL
try:
    DATABASE_URL, db_info = get_database_url()
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

    if os.getenv("TESTING") == "docker":
        logger.info(
            "Docker test env: PostgreSQL %s:%s/%s",
            db_info["host"],
            db_info["port"],
            db_info["db"],
        )
    elif os.getenv("TESTING") == "true":
        logger.info("Test env: SQLite in-memory DB")
    else:
        logger.info(
            "DB connection configured: %s@%s:%s/%s",
            db_info["user"],
            db_info["host"],
            db_info["port"],
            db_info["name"],
        )
except ValueError as e:
    logger.error("Environment variable error: %s", e)
    sys.exit(1)
except Exception as e:
    logger.error("Unexpected error: %s", e)
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
        logger.error("Database connection failed: %s", e)
        raise


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
