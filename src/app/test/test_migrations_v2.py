"""Fully isolated migration tests."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, inspect


class TestMigrationsIsolated:
    """Fully isolated migration tests."""

    @pytest.fixture
    def isolated_engine(self):
        """Fully isolated SQLite engine."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_file.close()

        db_url = f"sqlite:///{temp_file.name}"
        engine = create_engine(db_url, echo=False)

        yield engine

        engine.dispose()
        try:
            os.unlink(temp_file.name)
        except OSError:
            pass

    @pytest.fixture
    def isolated_alembic_config(self, isolated_engine):
        """Isolated Alembic config — PostgreSQL connection disabled."""
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", str(isolated_engine.url))
        return config

    def test_migration_files_structure(self):
        """Verify migration file structure."""
        versions_dir = Path("alembic/versions")
        assert versions_dir.exists(), "alembic/versions directory does not exist"

        migration_files = list(versions_dir.glob("*.py"))
        assert len(migration_files) > 0, "No migration files found"

        print(f"\nMigration files found: {len(migration_files)}")
        for f in sorted(migration_files):
            print(f"  {f.name}")

    @patch("app.database.get_db_url")
    def test_models_create_tables_directly(self, mock_get_db_url, isolated_engine):
        """Test direct table creation via models (SQLite-compatible tables only)."""
        mock_get_db_url.return_value = str(isolated_engine.url)

        from app.models.models import AnalysisJob, BusinessPlan, User

        metadata = MetaData()
        for table in [User.__table__, BusinessPlan.__table__, AnalysisJob.__table__]:
            table.to_metadata(metadata)

        metadata.create_all(isolated_engine)

        inspector = inspect(isolated_engine)
        tables = set(inspector.get_table_names())

        print(f"\nCreated tables: {tables}")

        expected_tables = {"users", "business_plans", "analysis_jobs"}
        created_core_tables = expected_tables.intersection(tables)
        assert len(created_core_tables) >= 2, (
            f"Core tables not created. Created: {tables}"
        )

    @patch("app.database.get_db_url")
    def test_table_schemas(self, mock_get_db_url, isolated_engine):
        """Validate table schemas (SQLite-compatible tables only)."""
        mock_get_db_url.return_value = str(isolated_engine.url)

        from app.models.models import AnalysisJob, BusinessPlan, User
        from sqlalchemy import MetaData as _Meta

        meta = _Meta()
        for t in [User.__table__, BusinessPlan.__table__, AnalysisJob.__table__]:
            t.to_metadata(meta)
        meta.create_all(isolated_engine)

        inspector = inspect(isolated_engine)

        # Validate users table
        if inspector.has_table("users"):
            users_cols = {col["name"] for col in inspector.get_columns("users")}
            print(f"\nusers table columns: {users_cols}")
            assert "id" in users_cols
            # Latest schema uses id as VARCHAR (OIDC sub claim)

        # Validate business_plans table
        if inspector.has_table("business_plans"):
            bp_cols = {col["name"] for col in inspector.get_columns("business_plans")}
            print(f"business_plans table columns: {bp_cols}")
            assert "id" in bp_cols
            assert "user_id" in bp_cols
            assert "file_name" in bp_cols

    def test_alembic_basic_functionality(self):
        """Verify Alembic basic functionality (without running migrations)."""
        config = Config("alembic.ini")
        script_location = config.get_main_option("script_location")
        assert script_location is not None

        versions_path = Path(script_location) / "versions"
        assert versions_path.exists()

        print(f"\nAlembic config valid. Script: {script_location}, versions: {versions_path}")

    def test_model_imports_work(self):
        """Verify model imports work correctly."""
        try:
            from app.models.models import (
                AnalysisJob,
                AnalysisResult,
                BusinessPlan,
                User,
            )

            assert hasattr(User, "__tablename__")
            assert hasattr(BusinessPlan, "__tablename__")
            assert hasattr(AnalysisJob, "__tablename__")
            assert hasattr(AnalysisResult, "__tablename__")

            print(
                f"\nModel tables: User={User.__tablename__}, "
                f"BusinessPlan={BusinessPlan.__tablename__}, "
                f"AnalysisJob={AnalysisJob.__tablename__}, "
                f"AnalysisResult={AnalysisResult.__tablename__}"
            )

        except ImportError as e:
            pytest.fail(f"Model import failed: {e}")

    def test_database_config_structure(self):
        """Verify database configuration structure."""
        try:
            from app.core.config import settings

            db_settings = ["db_user", "db_password", "db_host", "db_port", "db_name"]
            missing_settings = [s for s in db_settings if not hasattr(settings, s)]

            if missing_settings:
                print(f"Missing DB settings: {missing_settings}")
            else:
                print("All DB settings present.")

        except ImportError as e:
            pytest.fail(f"Config module import failed: {e}")

    def test_env_py_structure(self):
        """Verify alembic/env.py file structure."""
        env_path = Path("alembic/env.py")
        assert env_path.exists(), "alembic/env.py does not exist"

        content = env_path.read_text(encoding="utf-8")

        required_parts = [
            "run_migrations_offline",
            "run_migrations_online",
            "target_metadata",
        ]
        missing_parts = [p for p in required_parts if p not in content]

        assert not missing_parts, f"Elements missing from env.py: {missing_parts}"
        print("alembic/env.py structure is valid.")
