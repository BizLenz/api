"""perf: add performance indexes to analyses

Revision ID: 950a2b4ea482
Revises: ebd1084c8d48
Create Date: 2025-08-08 17:21:29.700674

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '950a2b4ea482'
down_revision: str | Sequence[str] | None = 'ebd1084c8d48'  # 🔧 수정됨
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add performance indexes to analyses table.
    
    Creates indexes to optimize common query patterns:
    - Status-based filtering
    - Business plan lookups
    - Gemini API tracking
    - Time-based sorting
    """
    
    # 🚀 핵심 단일 인덱스들 (가장 중요)
    op.create_index('idx_analyses_status', 'analyses', ['status'])
    op.create_index('idx_analyses_plan_id', 'analyses', ['plan_id'])
    op.create_index('idx_analyses_gemini_request_id', 'analyses', ['gemini_request_id'])
    
    # 🔥 복합 인덱스들 (성능 최적화)
    op.create_index('idx_analyses_plan_status', 'analyses', ['plan_id', 'status'])
    op.create_index('idx_analyses_status_created', 'analyses', ['status', 'created_at'])
    
    # ⏰ 시간 기반 조회 최적화
    op.create_index('idx_analyses_created_at_desc', 'analyses', [sa.text('created_at DESC')])
    
    # 📊 조건부 인덱스 (NULL 값 제외하여 공간 효율성 증대)
    op.create_index(
        'idx_analyses_completed_at_desc', 
        'analyses', 
        [sa.text('completed_at DESC')],
        postgresql_where=sa.text('completed_at IS NOT NULL')
    )
    
    op.create_index(
        'idx_analyses_overall_score_desc', 
        'analyses', 
        [sa.text('overall_score DESC')],
        postgresql_where=sa.text('overall_score IS NOT NULL')
    )
    
    # 🚨 에러 분석용 인덱스
    op.create_index(
        'idx_analyses_retry_count', 
        'analyses', 
        ['retry_count'],
        postgresql_where=sa.text('retry_count > 0')
    )


def downgrade() -> None:
    """
    Remove all performance indexes from analyses table.
    
    This function completely undoes all changes made by upgrade().
    """
    
    # 🗑️ 인덱스 삭제 (생성의 역순으로)
    op.drop_index('idx_analyses_retry_count', table_name='analyses')
    op.drop_index('idx_analyses_overall_score_desc', table_name='analyses')
    op.drop_index('idx_analyses_completed_at_desc', table_name='analyses')
    op.drop_index('idx_analyses_created_at_desc', table_name='analyses')
    op.drop_index('idx_analyses_status_created', table_name='analyses')
    op.drop_index('idx_analyses_plan_status', table_name='analyses')
    op.drop_index('idx_analyses_gemini_request_id', table_name='analyses')
    op.drop_index('idx_analyses_plan_id', table_name='analyses')
    op.drop_index('idx_analyses_status', table_name='analyses')