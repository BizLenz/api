"""refactor: update users table (id=VARCHAR, drop cognito_sub) and business_plans.user_id FK

Revision ID: 2c1302d295fb
Revises: 6f13884faeda
Create Date: 2025-09-07 18:34:53.250541

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2c1302d295fb"
down_revision: str | Sequence[str] | None = "6f13884faeda"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    # --- 1) Drop existing FK ---
    op.drop_constraint(
        "business_plans_user_id_fkey", "business_plans", type_="foreignkey"
    )

    # --- 2) Add users.updated_at ---
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
            comment="Profile last modified timestamp",
        ),
    )

    # --- 3) Drop default from users.id + change type to VARCHAR ---
    op.execute("ALTER TABLE users ALTER COLUMN id DROP DEFAULT")
    op.alter_column(
        "users",
        "id",
        existing_type=sa.INTEGER(),
        type_=sa.String(length=255),
        comment="OIDC sub claim (internal unique ID)",
        existing_nullable=False,
    )

    # --- 4) Change business_plans.user_id type to VARCHAR ---
    op.alter_column(
        "business_plans",
        "user_id",
        existing_type=sa.INTEGER(),
        type_=sa.String(length=255),
        existing_comment="Uploader user",
        existing_nullable=False,
    )

    # --- 5) Recreate FK constraint ---
    op.create_foreign_key(
        "business_plans_user_id_fkey",
        "business_plans",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # --- 6) Remove unused indexes and columns ---
    op.drop_index(op.f("idx_users_cognito_sub"), table_name="users")
    op.drop_index(op.f("idx_users_token_usage"), table_name="users")
    op.drop_constraint(op.f("users_cognito_sub_key"), "users", type_="unique")
    op.drop_column("users", "total_token_usage")
    op.drop_column("users", "cognito_sub")


def downgrade() -> None:
    """Downgrade schema."""

    # --- 1) Restore users.cognito_sub, total_token_usage ---
    op.add_column(
        "users",
        sa.Column(
            "cognito_sub",
            sa.VARCHAR(length=255),
            nullable=False,
            comment="Cognito user unique identifier (JWT sub)",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "total_token_usage",
            sa.INTEGER(),
            server_default=sa.text("0"),
            nullable=False,
            comment="Cumulative token usage",
        ),
    )
    op.create_unique_constraint(
        op.f("users_cognito_sub_key"),
        "users",
        ["cognito_sub"],
        postgresql_nulls_not_distinct=False,
    )
    op.create_index(
        op.f("idx_users_token_usage"), "users", ["total_token_usage"], unique=False
    )
    op.create_index(
        op.f("idx_users_cognito_sub"), "users", ["cognito_sub"], unique=False
    )

    # --- 2) Revert business_plans.user_id to INTEGER (after dropping FK) ---
    op.drop_constraint(
        "business_plans_user_id_fkey", "business_plans", type_="foreignkey"
    )

    # Explicit type cast in PostgreSQL (using USING clause)
    op.execute(
        "ALTER TABLE business_plans ALTER COLUMN user_id TYPE INTEGER USING user_id::integer"
    )

    # --- 3) Revert users.id to INTEGER + restore sequence default ---
    # Explicit type cast in PostgreSQL (using USING clause)
    op.execute("ALTER TABLE users ALTER COLUMN id TYPE INTEGER USING id::integer")

    # Restore sequence default
    op.execute(
        "ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('users_id_seq'::regclass)"
    )

    # Update column metadata
    op.alter_column(
        "users",
        "id",
        existing_type=sa.String(length=255),
        type_=sa.INTEGER(),
        comment="Internal unique ID",
        existing_comment="OIDC sub claim (internal unique ID)",
        existing_nullable=False,
        existing_server_default=sa.text("nextval('users_id_seq'::regclass)"),
    )

    # --- 4) Drop users.updated_at ---
    op.drop_column("users", "updated_at")

    # --- 5) Recreate FK ---
    op.create_foreign_key(
        "business_plans_user_id_fkey",
        "business_plans",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
