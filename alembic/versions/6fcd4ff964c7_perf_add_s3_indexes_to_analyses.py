"""perf_add_s3_indexes_to_analyses

Revision ID: 6fcd4ff964c7
Revises: ba206fae5a6b
Create Date: 2025-08-08 19:51:35.726880
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "6fcd4ff964c7"
down_revision: str | Sequence[str] | None = "ba206fae5a6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _comment_on_index(name: str, comment: str) -> None:
    """COMMENT ON INDEX with bound param (Alembic expects a single arg to execute)."""
    stmt = sa.text(f'COMMENT ON INDEX "{name}" IS :cmt').bindparams(
        sa.bindparam("cmt", value=comment)
    )
    op.execute(stmt)


def upgrade() -> None:
    """Add S3 performance optimization indexes."""

    # 1) S3 키별 빠른 검색 인덱스 (부분 인덱스)
    op.create_index(
        "idx_analyses_s3_key",
        "analyses",
        ["s3_key"],
        postgresql_where=sa.text("s3_key IS NOT NULL"),
    )
    _comment_on_index("idx_analyses_s3_key", "S3 키별 빠른 검색을 위한 인덱스")

    # 2) 업로드 상태별 조회 최적화
    op.create_index(
        "idx_analyses_upload_status",
        "analyses",
        ["upload_status"],
    )
    _comment_on_index("idx_analyses_upload_status", "업로드 상태별 필터링 최적화")

    # 3) 파일 크기별 정렬 최적화 (내림차순)
    op.create_index(
        "idx_analyses_file_size_desc",
        "analyses",
        [sa.text("file_size DESC")],
        postgresql_where=sa.text("file_size IS NOT NULL"),
    )
    _comment_on_index("idx_analyses_file_size_desc", "파일 크기별 정렬 최적화 (내림차순)")

    # 4) 다운로드 횟수별 정렬 최적화 (내림차순)
    op.create_index(
        "idx_analyses_download_count_desc",
        "analyses",
        [sa.text("download_count DESC")],
        postgresql_where=sa.text("download_count > 0"),
    )
    _comment_on_index(
        "idx_analyses_download_count_desc", "다운로드 횟수별 정렬 최적화 (내림차순)"
    )

    # 5) 아카이브 상태 및 날짜별 조회 최적화 (복합)
    op.create_index(
        "idx_analyses_archived_status",
        "analyses",
        ["is_archived", "archive_date"],
    )
    _comment_on_index("idx_analyses_archived_status", "아카이브 상태 및 날짜별 조회 최적화")

    # 6) S3 버킷-키 복합 인덱스
    op.create_index(
        "idx_analyses_s3_bucket_key",
        "analyses",
        ["s3_bucket", "s3_key"],
        postgresql_where=sa.text("s3_bucket IS NOT NULL AND s3_key IS NOT NULL"),
    )
    _comment_on_index("idx_analyses_s3_bucket_key", "S3 버킷-키 복합 조회 최적화")

    # 7) 마지막 접근 시간별 정렬 (내림차순)
    op.create_index(
        "idx_analyses_last_accessed_desc",
        "analyses",
        [sa.text("last_accessed_at DESC")],
        postgresql_where=sa.text("last_accessed_at IS NOT NULL"),
    )
    _comment_on_index("idx_analyses_last_accessed_desc", "마지막 접근 시간별 정렬 최적화")

    # 8) 업로드 완료 시간별 정렬 (내림차순)
    op.create_index(
        "idx_analyses_upload_completed_desc",
        "analyses",
        [sa.text("upload_completed_at DESC")],
        postgresql_where=sa.text("upload_completed_at IS NOT NULL"),
    )
    _comment_on_index("idx_analyses_upload_completed_desc", "업로드 완료 시간별 정렬 최적화")

    # 9) 프리사인드 URL 만료 관리
    op.create_index(
        "idx_analyses_presigned_expires",
        "analyses",
        ["presigned_url_expires_at"],
        postgresql_where=sa.text("presigned_url_expires_at IS NOT NULL"),
    )
    _comment_on_index("idx_analyses_presigned_expires", "프리사인드 URL 만료 시간 관리 최적화")


def downgrade() -> None:
    """Remove S3 performance optimization indexes."""
    # 인덱스 제거 (역순)
    op.drop_index("idx_analyses_presigned_expires", table_name="analyses")
    op.drop_index("idx_analyses_upload_completed_desc", table_name="analyses")
    op.drop_index("idx_analyses_last_accessed_desc", table_name="analyses")
    op.drop_index("idx_analyses_s3_bucket_key", table_name="analyses")
    op.drop_index("idx_analyses_archived_status", table_name="analyses")
    op.drop_index("idx_analyses_download_count_desc", table_name="analyses")
    op.drop_index("idx_analyses_file_size_desc", table_name="analyses")
    op.drop_index("idx_analyses_upload_status", table_name="analyses")
    op.drop_index("idx_analyses_s3_key", table_name="analyses")
