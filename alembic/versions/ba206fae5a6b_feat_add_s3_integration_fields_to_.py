"""feat_add_s3_integration_fields_to_analyses

Revision ID: ba206fae5a6b
Revises: 950a2b4ea482
Create Date: 2025-08-08 18:30:58.384202

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba206fae5a6b'
down_revision: str | Sequence[str] | None = '950a2b4ea482'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add S3 integration fields to analyses table."""
    
    # 1. S3 저장소 관련 필드
    op.add_column('analyses', sa.Column('s3_bucket', sa.String(255), nullable=True, 
                  comment='S3 버킷명'))
    op.add_column('analyses', sa.Column('s3_key', sa.String(500), nullable=True,
                  comment='S3 객체 키 (파일 경로)'))
    op.add_column('analyses', sa.Column('s3_region', sa.String(50), nullable=True,
                  server_default='ap-northeast-2', comment='S3 리전'))
    
    # 2. 파일 메타데이터 필드
    op.add_column('analyses', sa.Column('file_size', sa.BigInteger, nullable=True,
                  comment='파일 크기 (bytes)'))
    op.add_column('analyses', sa.Column('file_checksum', sa.String(64), nullable=True,
                  comment='파일 체크섬 (SHA256)'))
    op.add_column('analyses', sa.Column('content_type', sa.String(100), nullable=True,
                  comment='파일 MIME 타입'))
    
    # 3. 업로드 상태 관리 필드
    upload_status_enum = sa.Enum('pending', 'uploading', 'completed', 'failed', 
                                name='upload_status_enum', create_type=False)
    upload_status_enum.create(op.get_bind(), checkfirst=True)
    
    op.add_column('analyses', sa.Column('upload_status', upload_status_enum,
                  server_default='pending', comment='S3 업로드 상태'))
    op.add_column('analyses', sa.Column('upload_started_at', 
                  sa.DateTime(timezone=True), nullable=True,
                  comment='업로드 시작 시간'))
    op.add_column('analyses', sa.Column('upload_completed_at', 
                  sa.DateTime(timezone=True), nullable=True,
                  comment='업로드 완료 시간'))
    
    # 4. S3 접근 관리 필드
    op.add_column('analyses', sa.Column('presigned_url_expires_at', 
                  sa.DateTime(timezone=True), nullable=True,
                  comment='프리사인드 URL 만료 시간'))
    op.add_column('analyses', sa.Column('download_count', sa.Integer, 
                  server_default='0', comment='다운로드 횟수'))
    op.add_column('analyses', sa.Column('last_accessed_at', 
                  sa.DateTime(timezone=True), nullable=True,
                  comment='마지막 접근 시간'))
    
    # 5. 백업 및 버전 관리 필드
    op.add_column('analyses', sa.Column('backup_s3_key', sa.String(500), nullable=True,
                  comment='백업 S3 키'))
    op.add_column('analyses', sa.Column('version_id', sa.String(100), nullable=True,
                  comment='S3 객체 버전 ID'))
    op.add_column('analyses', sa.Column('is_archived', sa.Boolean, 
                  server_default='false', comment='아카이브 여부'))
    op.add_column('analyses', sa.Column('archive_date', 
                  sa.DateTime(timezone=True), nullable=True,
                  comment='아카이브 날짜'))


def downgrade() -> None:
    """Remove S3 integration fields from analyses table."""
    
    # S3 관련 필드들 제거 (역순으로)
    op.drop_column('analyses', 'archive_date')
    op.drop_column('analyses', 'is_archived')
    op.drop_column('analyses', 'version_id')
    op.drop_column('analyses', 'backup_s3_key')
    
    op.drop_column('analyses', 'last_accessed_at')
    op.drop_column('analyses', 'download_count')
    op.drop_column('analyses', 'presigned_url_expires_at')
    
    op.drop_column('analyses', 'upload_completed_at')
    op.drop_column('analyses', 'upload_started_at')
    op.drop_column('analyses', 'upload_status')
    
    # Enum 타입 삭제
    upload_status_enum = sa.Enum(name='upload_status_enum')
    upload_status_enum.drop(op.get_bind(), checkfirst=True)
    
    op.drop_column('analyses', 'content_type')
    op.drop_column('analyses', 'file_checksum')
    op.drop_column('analyses', 'file_size')
    
    op.drop_column('analyses', 's3_region')
    op.drop_column('analyses', 's3_key')
    op.drop_column('analyses', 's3_bucket')