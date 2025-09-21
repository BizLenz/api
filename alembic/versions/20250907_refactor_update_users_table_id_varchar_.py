"""refactor: update users table (id=VARCHAR, drop cognito_sub) and business_plans.user_id FK

Revision ID: 2c1302d295fb
Revises: 6f13884faeda
Create Date: 2025-09-07 18:34:53.250541

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c1302d295fb'
down_revision: str | Sequence[str] | None = '6f13884faeda'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    # --- 1) 기존 FK 제거 ---
    op.drop_constraint('business_plans_user_id_fkey', 'business_plans', type_='foreignkey')

    # --- 2) users.updated_at 추가 ---
    op.add_column(
        'users',
        sa.Column(
            'updated_at',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('now()'),
            nullable=True,
            comment='프로필 수정 일시'
        )
    )

    # --- 3) users.id 기본값 제거 + VARCHAR로 타입 변경 ---
    op.execute("ALTER TABLE users ALTER COLUMN id DROP DEFAULT")
    op.alter_column(
        'users',
        'id',
        existing_type=sa.INTEGER(),
        type_=sa.String(length=255),
        comment='Cognito Sub (서비스 내부 고유 ID)',
        existing_nullable=False,
    )

    # --- 4) business_plans.user_id VARCHAR로 타입 변경 ---
    op.alter_column(
        'business_plans',
        'user_id',
        existing_type=sa.INTEGER(),
        type_=sa.String(length=255),
        existing_comment='업로더 사용자',
        existing_nullable=False,
    )

    # --- 5) FK 제약조건 다시 생성 ---
    op.create_foreign_key(
        'business_plans_user_id_fkey',
        'business_plans', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )

    # --- 6) 불필요한 인덱스 및 컬럼 제거 ---
    op.drop_index(op.f('idx_users_cognito_sub'), table_name='users')
    op.drop_index(op.f('idx_users_token_usage'), table_name='users')
    op.drop_constraint(op.f('users_cognito_sub_key'), 'users', type_='unique')
    op.drop_column('users', 'total_token_usage')
    op.drop_column('users', 'cognito_sub')


def downgrade() -> None:
    """Downgrade schema."""

    # --- 1) users.cognito_sub, total_token_usage 복구 ---
    op.add_column(
        'users',
        sa.Column(
            'cognito_sub',
            sa.VARCHAR(length=255),
            nullable=False,
            comment='Cognito 사용자 고유 식별자 (JWT sub)'
        )
    )
    op.add_column(
        'users',
        sa.Column(
            'total_token_usage',
            sa.INTEGER(),
            server_default=sa.text('0'),
            nullable=False,
            comment='누적 토큰 사용량'
        )
    )
    op.create_unique_constraint(op.f('users_cognito_sub_key'), 'users', ['cognito_sub'], postgresql_nulls_not_distinct=False)
    op.create_index(op.f('idx_users_token_usage'), 'users', ['total_token_usage'], unique=False)
    op.create_index(op.f('idx_users_cognito_sub'), 'users', ['cognito_sub'], unique=False)

    # --- 2) business_plans.user_id 다시 INTEGER로 변경 (FK 제거 후) ---
    op.drop_constraint('business_plans_user_id_fkey', 'business_plans', type_='foreignkey')
    
    # PostgreSQL에서 명시적 타입 변환 (USING 절 사용)
    op.execute("ALTER TABLE business_plans ALTER COLUMN user_id TYPE INTEGER USING user_id::integer")

    # --- 3) users.id 다시 INTEGER + 시퀀스 기본값 복구 ---
    # PostgreSQL에서 명시적 타입 변환 (USING 절 사용)
    op.execute("ALTER TABLE users ALTER COLUMN id TYPE INTEGER USING id::integer")
    
    # 시퀀스 기본값 복구
    op.execute("ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('users_id_seq'::regclass)")
    
    # 컬럼 메타데이터 업데이트
    op.alter_column(
        'users',
        'id',
        existing_type=sa.String(length=255),
        type_=sa.INTEGER(),
        comment='서비스 내부 고유 ID',
        existing_comment='Cognito Sub (서비스 내부 고유 ID)',
        existing_nullable=False,
        existing_server_default=sa.text("nextval('users_id_seq'::regclass)")
    )

    # --- 4) users.updated_at 제거 ---
    op.drop_column('users', 'updated_at')

    # --- 5) FK 다시 생성 ---
    op.create_foreign_key(
        'business_plans_user_id_fkey',
        'business_plans', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )