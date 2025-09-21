"""
간단한 마이그레이션 테스트 - 핵심 기능만
파일 위치: test/test_migrations.py
"""

import pytest
from sqlalchemy import create_engine, inspect
from alembic.config import Config
from alembic import command



class TestMigrations:
    """마이그레이션 기본 테스트"""

    @pytest.fixture
    def temp_engine(self):
        """테스트용 SQLite 엔진"""
        engine = create_engine("sqlite:///:memory:")
        yield engine
        engine.dispose()

    @pytest.fixture
    def alembic_config(self, temp_engine):
        """Alembic 설정"""
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", str(temp_engine.url))
        return config

    def test_upgrade_creates_tables(self, temp_engine, alembic_config):
        """upgrade() 함수가 테이블을 생성하는지 테스트"""

        with temp_engine.connect() as connection:
            alembic_config.attributes["connection"] = connection

            # upgrade 실행
            command.upgrade(alembic_config, "head")

            # 테이블이 생성되었는지 확인
            inspector = inspect(temp_engine)
            tables = inspector.get_table_names()

            expected_tables = {"users", "business_plans", "analysis_jobs"}  # analyses -> analysis_jobs
            assert expected_tables.issubset(tables), (
                f"Expected tables not created: {expected_tables}"
            )

    def test_analyses_has_gemini_fields(self, temp_engine, alembic_config):
        """analyses 테이블에 Gemini 필드가 있는지 테스트"""

        with temp_engine.connect() as connection:
            alembic_config.attributes["connection"] = connection
            command.upgrade(alembic_config, "head")

            inspector = inspect(temp_engine)
            columns = inspector.get_columns("analysis_jobs")  # analyses -> analysis_jobs
            column_names = {col["name"] for col in columns}

            # 핵심 Gemini 필드들만 확인
            gemini_fields = {"status", "progress", "gemini_request_id", "overall_score"}
            missing = gemini_fields - column_names

            assert not missing, f"Missing Gemini fields: {missing}"

    def test_upgrade_downgrade_cycle(self, temp_engine, alembic_config):
        """upgrade → downgrade가 제대로 작동하는지 테스트"""

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
