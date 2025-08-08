"""perf_add_s3_indexes_to_analyses

Revision ID: 6fcd4ff964c7
Revises: ba206fae5a6b
Create Date: 2025-08-08 19:51:35.726880

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6fcd4ff964c7'
down_revision: str | Sequence[str] | None = 'ba206fae5a6b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass