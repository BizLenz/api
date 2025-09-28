"""
간단한 마이그레이션 테스트 - 핵심 기능만
파일 위치: test/test_migrations.py
"""

import pytest
from sqlalchemy import create_engine, inspect
from alembic.config import Config
from alembic import command
import os

os.environ["TESTING"] = "docker"  # 테스트 파일 시작에 추가


class TestMigrations:
    """마이그레이션 기본 테스트"""

    @pytest.fixture
    def temp_engine(self):
        """환경에 따른 DB 엔진"""
        if os.getenv("TESTING") == "docker":
            # Docker PostgreSQL 사용
            engine = create_engine(
                "postgresql://test_user:test123@localhost:5433/bizlenz_test"
            )
        else:
            # 기본 SQLite 사용
            engine = create_engine("sqlite:///:memory:")

        yield engine
        engine.dispose()

    @pytest.fixture
    def alembic_config(self, temp_engine):
        """Alembic 설정"""
        config = Config("alembic.ini")

        # Docker 환경에서는 env.py가 자동으로 URL 설정
        if os.getenv("TESTING") != "docker":
            config.set_main_option("sqlalchemy.url", str(temp_engine.url))

        return config

    def test_upgrade_creates_tables(self, temp_engine, alembic_config):
        """upgrade() 함수가 테이블을 생성하는지 테스트"""

        if os.getenv("TESTING") == "docker":
            # Docker PostgreSQL: env.py가 직접 연결 관리
            command.upgrade(alembic_config, "head")

            # 테이블 확인
            inspector = inspect(temp_engine)
            tables = inspector.get_table_names()
        else:
            # SQLite: 기존 방식
            with temp_engine.connect() as connection:
                alembic_config.attributes["connection"] = connection
                command.upgrade(alembic_config, "head")

                inspector = inspect(temp_engine)
                tables = inspector.get_table_names()

        expected_tables = {
            "users",
            "business_plans",
            "analysis_jobs",
        }  # analyses -> analysis_jobs
        assert expected_tables.issubset(tables), (
            f"Expected tables not created: {expected_tables}"
        )

    def test_analyses_has_gemini_fields(self, temp_engine, alembic_config):
        """analysis_jobs 테이블에 필드가 있는지 테스트"""

        if os.getenv("TESTING") == "docker":
            # Docker PostgreSQL
            command.upgrade(alembic_config, "head")
            inspector = inspect(temp_engine)
        else:
            # SQLite
            with temp_engine.connect() as connection:
                alembic_config.attributes["connection"] = connection
                command.upgrade(alembic_config, "head")
                inspector = inspect(temp_engine)

        columns = inspector.get_columns("analysis_jobs")  # analyses -> analysis_jobs
        column_names = {col["name"] for col in columns}

        # 실제 존재하는 필드들 확인 (models.py의 AnalysisJob 기준)
        expected_fields = {"id", "plan_id", "job_type", "status", "created_at"}
        missing = expected_fields - column_names

        assert not missing, f"Missing expected fields: {missing}"

    def test_upgrade_downgrade_cycle(self, temp_engine, alembic_config):
        """upgrade → downgrade가 제대로 작동하는지 테스트"""

        if os.getenv("TESTING") == "docker":
            # Docker PostgreSQL
            # 먼저 베이스로 다운그레이드 (깨끗한 상태로 시작)
            command.downgrade(alembic_config, "base")

            inspector = inspect(temp_engine)
            initial_tables = set(inspector.get_table_names())

            # upgrade
            command.upgrade(alembic_config, "head")
            inspector = inspect(temp_engine)
            after_upgrade = set(inspector.get_table_names())

            # 테이블이 추가되었는지 확인
            assert len(after_upgrade) > len(initial_tables), (
                "No tables created during upgrade"
            )

            # downgrade
            command.downgrade(alembic_config, "base")
            inspector = inspect(temp_engine)
            after_downgrade = set(inspector.get_table_names())

            # alembic_version 테이블 제외하고 원복되었는지 확인
            user_tables_after_downgrade = after_downgrade - {"alembic_version"}
            assert user_tables_after_downgrade == initial_tables, (
                "Downgrade didn't restore original state"
            )
        else:
            # SQLite
            with temp_engine.connect() as connection:
                alembic_config.attributes["connection"] = connection

                # 초기 상태
                inspector = inspect(temp_engine)
                initial_tables = set(inspector.get_table_names())

                # upgrade
                command.upgrade(alembic_config, "head")
                inspector = inspect(temp_engine)
                after_upgrade = set(inspector.get_table_names())

                # 테이블이 추가되었는지 확인
                assert len(after_upgrade) > len(initial_tables), (
                    "No tables created during upgrade"
                )

                # downgrade
                command.downgrade(alembic_config, "base")
                inspector = inspect(temp_engine)
                after_downgrade = set(inspector.get_table_names())

                # alembic_version 테이블 제외하고 원복되었는지 확인
                user_tables_after_downgrade = after_downgrade - {"alembic_version"}
                assert user_tables_after_downgrade == initial_tables, (
                    "Downgrade didn't restore original state"
                )
