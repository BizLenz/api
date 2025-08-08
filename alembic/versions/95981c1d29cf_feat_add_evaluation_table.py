"""feat_add_evaluation_table

Revision ID: 95981c1d29cf
Revises: 6fcd4ff964c7
Create Date: 2025-08-08 20:22:43.729887

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY


# revision identifiers, used by Alembic.
revision: str = '95981c1d29cf'
down_revision: str | Sequence[str] | None = '6fcd4ff964c7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create evaluation table for detailed analysis evaluations."""
    
    # Evaluation 테이블 생성
    op.create_table(
        'evaluations',
        
        # 기본 필드
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, 
                  comment='평가 ID'),
        sa.Column('analysis_id', sa.Integer, sa.ForeignKey('analyses.id', ondelete='CASCADE'), 
                  nullable=False, comment='분석 ID (외래키)'),
        
        # 평가 기본 정보
        sa.Column('evaluation_type', sa.String(50), nullable=False,
                  comment='평가 유형 (overall, market, financial, technical, risk)'),
        sa.Column('evaluation_category', sa.String(100), nullable=True,
                  comment='평가 카테고리 (세부 분류)'),
        sa.Column('score', sa.Numeric(5, 2), nullable=True,
                  comment='평가 점수 (0.00-100.00)'),
        sa.Column('grade', sa.String(10), nullable=True,
                  comment='평가 등급 (A+, A, B+, B, C+, C, D, F)'),
        
        # 평가 상세 내용
        sa.Column('title', sa.String(200), nullable=False,
                  comment='평가 제목'),
        sa.Column('summary', sa.Text, nullable=True,
                  comment='평가 요약'),
        sa.Column('detailed_feedback', sa.Text, nullable=True,
                  comment='상세 피드백'),
        sa.Column('strengths', ARRAY(sa.Text), nullable=True,
                  comment='강점 목록'),
        sa.Column('weaknesses', ARRAY(sa.Text), nullable=True,
                  comment='약점 목록'),
        sa.Column('recommendations', ARRAY(sa.Text), nullable=True,
                  comment='개선 제안사항'),
        
        # 평가 메타데이터
        sa.Column('evaluation_criteria', JSONB, nullable=True,
                  comment='평가 기준 정보'),
        sa.Column('metrics', JSONB, nullable=True,
                  comment='평가 지표 및 세부 점수'),
        sa.Column('benchmark_data', JSONB, nullable=True,
                  comment='벤치마크 데이터'),
        
        # 가중치 및 중요도
        sa.Column('weight', sa.Numeric(5, 4), default=1.0000,
                  comment='평가 가중치 (0.0000-1.0000)'),
        sa.Column('importance_level', sa.String(20), default='medium',
                  comment='중요도 (critical, high, medium, low)'),
        
        # 평가 상태 관리
        sa.Column('status', sa.String(20), default='completed',
                  comment='평가 상태 (pending, processing, completed, failed)'),
        sa.Column('confidence_score', sa.Numeric(5, 2), nullable=True,
                  comment='평가 신뢰도 (0.00-100.00)'),
        
        # 평가자 정보
        sa.Column('evaluator_type', sa.String(50), default='ai',
                  comment='평가자 유형 (ai, human, hybrid)'),
        sa.Column('evaluator_info', JSONB, nullable=True,
                  comment='평가자 상세 정보'),
        
        # 시간 정보
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now(), comment='평가 생성 시간'),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now(), onupdate=sa.func.now(),
                  comment='평가 수정 시간'),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True,
                  comment='평가 완료 시간'),
        
        # 버전 관리
        sa.Column('version', sa.Integer, default=1,
                  comment='평가 버전'),
        sa.Column('parent_evaluation_id', sa.Integer, 
                  sa.ForeignKey('evaluations.id', ondelete='SET NULL'), nullable=True,
                  comment='부모 평가 ID (재평가 시 참조)'),
        
        # 테이블 설정
        comment='상세 평가 결과 저장 테이블'
    )
    
    # 인덱스 생성
    # 1. 기본 조회 인덱스
    op.create_index('idx_evaluations_analysis_id', 'evaluations', ['analysis_id'])
    op.create_index('idx_evaluations_type', 'evaluations', ['evaluation_type'])
    op.create_index('idx_evaluations_status', 'evaluations', ['status'])
    
    # 2. 점수별 정렬 인덱스
    op.create_index('idx_evaluations_score_desc', 'evaluations', 
                    [sa.text('score DESC')],
                    postgresql_where=sa.text("score IS NOT NULL"))
    
    # 3. 복합 인덱스
    op.create_index('idx_evaluations_analysis_type', 'evaluations', 
                    ['analysis_id', 'evaluation_type'])
    op.create_index('idx_evaluations_type_score', 'evaluations', 
                    ['evaluation_type', sa.text('score DESC')])
    
    # 4. 시간별 정렬 인덱스
    op.create_index('idx_evaluations_created_desc', 'evaluations', 
                    [sa.text('created_at DESC')])
    op.create_index('idx_evaluations_evaluated_desc', 'evaluations', 
                    [sa.text('evaluated_at DESC')],
                    postgresql_where=sa.text("evaluated_at IS NOT NULL"))
    
    # 5. 중요도별 조회 인덱스
    op.create_index('idx_evaluations_importance', 'evaluations', 
                    ['importance_level', sa.text('score DESC')])


def downgrade() -> None:
    """Drop evaluation table and related indexes."""
    
    # 인덱스 삭제
    op.drop_index('idx_evaluations_importance', 'evaluations')
    op.drop_index('idx_evaluations_evaluated_desc', 'evaluations')
    op.drop_index('idx_evaluations_created_desc', 'evaluations')
    op.drop_index('idx_evaluations_type_score', 'evaluations')
    op.drop_index('idx_evaluations_analysis_type', 'evaluations')
    op.drop_index('idx_evaluations_score_desc', 'evaluations')
    op.drop_index('idx_evaluations_status', 'evaluations')
    op.drop_index('idx_evaluations_type', 'evaluations')
    op.drop_index('idx_evaluations_analysis_id', 'evaluations')
    
    # 테이블 삭제
    op.drop_table('evaluations')