import logging
from typing import Optional, Dict, Any
from uuid import uuid4

from botocore.exceptions import ClientError, BotoCoreError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import PlanStatus
from app.core.exceptions import to_http_exception
from app.core.security import get_claims, require_scope
from app.crud.file_metadata import create_business_plan
from app.crud.user import get_or_create_user
from app.database import get_db
from app.models import BusinessPlan
from app.schemas.file_schemas import FileMetadataSaveRequest, PresignedUrlRequest
from app.services.s3_service import make_boto3_client

logger = logging.getLogger(__name__)

# bizlenz/read scope is always a must
files = APIRouter(dependencies=[Depends(require_scope("bizlenz/read"))])


def _storage_file_url(bucket: str, key: str) -> str:
    """Build a public object URL for the configured storage backend"""
    if settings.storage_endpoint_url:
        # S3-compatible backend (MinIO, R2, etc.)
        endpoint = settings.storage_endpoint_url.rstrip("/")
        return f"{endpoint}/{bucket}/{key}"
    # AWS S3 — use path-style URL (works with any region)
    region = settings.storage_region or "us-east-1"
    return f"https://s3.{region}.amazonaws.com/{bucket}/{key}"


def _extract_s3_key(file_path: str) -> str:
    """
    Extract the object key from a stored file_path

    file_path may be:
    - A bare S3 key (uploads/uuid_filename.pdf)
    - A full URL (https://s3.region.amazonaws.com/bucket/key or https://endpoint/bucket/key)
    """
    if "://" not in file_path:
        # Already a bare key
        return file_path
    # Strip scheme + host + (optional bucket segment) to get the key
    path = file_path.split("://", 1)[1]  # host/path...
    parts = path.split("/", 1)
    rest = parts[1] if len(parts) > 1 else ""
    # If storage_endpoint_url is set the URL pattern is endpoint/bucket/key
    # so rest = bucket/key — strip the bucket prefix.
    bucket = settings.storage_bucket_name
    if rest.startswith(bucket + "/"):
        return rest[len(bucket) + 1 :]
    return rest


def is_admin(claims: Dict[str, Any]) -> bool:
    """Check for admin group membership"""
    groups = claims.get("groups", [])
    return "admin" in groups or "administrators" in groups


def get_or_ensure_user(db: Session, user_id: str) -> str:
    get_or_create_user(db, user_id=user_id)
    return user_id


def get_current_user_id(claims: Dict[str, Any]) -> str:
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found in token claims",
        )
    return user_id


def serialize_business_plan(file: BusinessPlan) -> dict:
    return {
        "id": file.id,
        "file_name": file.file_name,
        "file_path": file.file_path,
        "mime_type": file.mime_type,
        "file_size": file.file_size,
        "status": file.status,
        "created_at": file.created_at.isoformat() if file.created_at else None,
        "updated_at": file.updated_at.isoformat() if file.updated_at else None,
        "latest_job_id": file.latest_job_id,
    }


#####################################
# Upload endpoints                  #
#####################################


@files.post("/upload", response_model=dict)
def upload(
    file_details: PresignedUrlRequest,
    claims: Dict[str, Any] = Depends(require_scope("bizlenz/write")),
):
    """Generate a pre-signed URL for direct file upload to storage"""
    try:
        user_id = get_current_user_id(claims)

        s3_object_key_basename = f"{uuid4()}_{file_details.file_name}"
        s3_full_key = f"{settings.s3_upload_folder}/{s3_object_key_basename}"

        s3_client = make_boto3_client()
        url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.storage_bucket_name,
                "Key": s3_full_key,
                "ContentType": file_details.mime_type,
            },
            ExpiresIn=settings.presigned_url_expiration,
        )

        return {
            "user_id": user_id,
            "file_name": file_details.file_name,
            "mime_type": file_details.mime_type,
            "file_size": file_details.file_size,
            "success": True,
            "message": "Presigned URL generated successfully",
            "presigned_url": url,
            "key": s3_full_key,
            "file_url": _storage_file_url(settings.storage_bucket_name, s3_full_key),
        }
    except (ClientError, BotoCoreError, Exception) as err:
        raise to_http_exception(err)


@files.post("/upload/metadata", response_model=dict)
def save_file_metadata(
    metadata: FileMetadataSaveRequest,
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(require_scope("bizlenz/write")),
):
    """Save file metadata to DB after a successful direct upload"""
    try:
        if not metadata.s3_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="s3_key is required for metadata saving.",
            )
        if not metadata.s3_file_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="s3_file_url is required for metadata saving.",
            )

        user_id = get_or_ensure_user(db, get_current_user_id(claims))
        db_business_plan = create_business_plan(db, metadata, user_id=user_id)

        return {
            "success": True,
            "message": "File metadata saved successfully",
            "file_id": db_business_plan.id,
            "user_id": user_id,
            "status": "pending",
            "created_at": (
                db_business_plan.created_at.isoformat()
                if db_business_plan.created_at
                else None
            ),
            "updated_at": (
                db_business_plan.updated_at.isoformat()
                if db_business_plan.updated_at
                else None
            ),
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error saving file metadata")
        raise HTTPException(status_code=500, detail="Error saving file metadata")


#####################################
# Search endpoints                  #
#####################################


@files.get("/search", response_model=dict)
def search_my_files(
    keywords: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
):
    """Search the current user's uploaded files"""
    user_id = get_current_user_id(claims)
    query = db.query(BusinessPlan).filter(BusinessPlan.user_id == user_id)

    if keywords:
        query = query.filter(BusinessPlan.file_name.ilike(f"%{keywords}%"))

    if status_filter:
        if status_filter not in list(PlanStatus):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status filter"
            )
        query = query.filter(BusinessPlan.status == status_filter)

    _files = query.order_by(desc(BusinessPlan.created_at)).limit(limit).all()
    return {"success": True, "results": [serialize_business_plan(f) for f in _files]}


@files.get("/", response_model=dict)
def get_my_files(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
):
    """List all files uploaded by the current user; newest first"""
    user_id = get_current_user_id(claims)
    _files = (
        db.query(BusinessPlan)
        .filter(BusinessPlan.user_id == user_id)
        .order_by(desc(BusinessPlan.created_at))
        .limit(limit)
        .offset(offset)
        .all()
    )
    return {"success": True, "results": [serialize_business_plan(f) for f in _files]}


#####################################
# Delete / Download                 #
#####################################


@files.delete("/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(require_scope("bizlenz/write")),
):
    """Delete a file from storage and remove its DB record"""
    user_id = get_current_user_id(claims)
    try:
        file = db.query(BusinessPlan).filter(BusinessPlan.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        if file.user_id != user_id and not is_admin(claims):
            raise HTTPException(status_code=403, detail="Permission denied")

        if file.file_path:
            s3_key = _extract_s3_key(file.file_path)
            s3_client = make_boto3_client()
            s3_client.delete_object(Bucket=settings.storage_bucket_name, Key=s3_key)

        db.delete(file)
        db.commit()
        return {
            "success": True,
            "message": "File deleted successfully",
            "deleted_file_id": file_id,
        }

    except (ClientError, BotoCoreError):
        db.rollback()
        raise HTTPException(
            status_code=500, detail="File deletion failed: storage error"
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Error deleting file %s", file_id)
        raise HTTPException(status_code=500, detail="Error deleting file")


@files.get("/{file_id}/download", response_model=dict)
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
):
    """Generate a temporary pre-signed download URL for a file"""
    user_id = get_current_user_id(claims)
    try:
        _file = (
            db.query(BusinessPlan)
            .filter(BusinessPlan.id == file_id, BusinessPlan.user_id == user_id)
            .first()
        )
        if not _file:
            raise HTTPException(
                status_code=404, detail="File not found or access denied"
            )
        if not _file.file_path:
            raise HTTPException(status_code=404, detail="File path not found")

        s3_key = _extract_s3_key(_file.file_path)
        s3_client = make_boto3_client()
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.storage_bucket_name, "Key": s3_key},
            ExpiresIn=settings.presigned_url_expiration,
        )
        return {
            "success": True,
            "file_id": file_id,
            "file_name": _file.file_name,
            "presigned_url": presigned_url,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error preparing download for file %s", file_id)
        raise HTTPException(status_code=500, detail="Error preparing file download")


#####################################
# Admin endpoints                   #
#####################################


@files.get("/admin/all", response_model=dict)
def get_all_files_admin(
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Admin: list all files across all users"""
    if not is_admin(claims):
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        _files = (
            db.query(BusinessPlan)
            .order_by(desc(BusinessPlan.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return {"success": True, "results": [serialize_business_plan(f) for f in _files]}
    except Exception:
        logger.exception("Error retrieving all files (admin)")
        raise HTTPException(status_code=500, detail="Error retrieving all files")


@files.get("/admin/search", response_model=dict)
def search_all_files_admin(
    keywords: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
    limit: int = Query(100, ge=1, le=500),
):
    """Admin: search all files across all users"""
    if not is_admin(claims):
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        query = db.query(BusinessPlan)
        if keywords:
            query = query.filter(BusinessPlan.file_name.ilike(f"%{keywords}%"))
        if user_id:
            query = query.filter(BusinessPlan.user_id == user_id)
        if status_filter:
            if status_filter not in list(PlanStatus):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid status filter",
                )
            query = query.filter(BusinessPlan.status == status_filter)
        _files = query.order_by(desc(BusinessPlan.created_at)).limit(limit).all()
        return {"success": True, "results": [serialize_business_plan(f) for f in _files]}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error searching files (admin)")
        raise HTTPException(status_code=500, detail="Error searching files")
