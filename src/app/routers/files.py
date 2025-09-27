from fastapi import APIRouter, HTTPException, Query, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError, BotoCoreError
from uuid import uuid4
from app.crud.file_metadata import create_business_plan
from app.core.config import settings
from app.database import get_db
from app.core.security import require_scope, get_claims
from app.core.exceptions import to_http_exception
from app.crud.user import get_or_create_user
from app.models import BusinessPlan
import boto3

from app.schemas.file_schemas import PresignedUrlRequest, FileMetadataSaveRequest

# bizlenz/read scope is always a must
#files = APIRouter(dependencies=[Depends(require_scope("bizlenz/read"))])
files = APIRouter()

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
)


def is_admin(claims: Dict[str, Any]) -> bool:
    """Check for admin group"""
    groups = claims.get("cognito:groups", [])
    return "admin" in groups or "administrators" in groups


def get_user_by_cognito_sub(db: Session, cognito_sub: str) -> str:
    """cognito_sub를 그대로 user_id로 사용"""
    get_or_create_user(db, cognito_sub=cognito_sub)
    return cognito_sub


def get_current_user_id(claims: Dict[str, Any]) -> str:
    """Get user ID(sub) from JWT claims"""
    cognito_sub = claims.get("sub")
    if not cognito_sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found in token claims",
        )
    return cognito_sub


def serialize_business_plan(file: BusinessPlan) -> dict:
    """BusinessPlan ORM object -> dict"""
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
# Start of Upload-related endpoints #
#####################################


@files.post("/upload", response_model=dict)
def upload(
    file_details: PresignedUrlRequest,
    claims: Dict[str, Any] = Depends(require_scope("bizlenz/write")),
):
    """Make presigned URL for file upload"""
    try:
        user_id = get_current_user_id(claims)

        s3_object_key_basename = f"{uuid4()}_{file_details.file_name}"
        s3_full_key = f"{settings.s3_upload_folder}/{s3_object_key_basename}"

        params = {
            "Bucket": settings.s3_bucket_name,
            "Key": s3_full_key,
            "ContentType": file_details.mime_type,
        }

        url = s3_client.generate_presigned_url(
            "put_object",
            Params=params,
            ExpiresIn=300,
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
            "file_url": f"https://{settings.s3_bucket_name}.s3.amazonaws.com/{s3_full_key}",
        }
    except (ClientError, BotoCoreError, Exception) as err:
        raise to_http_exception(err)


@files.post("/upload/metadata", response_model=dict)
def save_file_metadata(
    metadata: FileMetadataSaveRequest,
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(require_scope("bizlenz/write")),
):
    """Upload to S3(/upload) -> save metadata to DB"""
    try:
        if not metadata.s3_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="S3 object key (s3_key) is required for metadata saving.",
            )
        if not metadata.s3_file_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="S3 file URL (s3_file_url) is required for metadata saving.",
            )

        user_id = get_user_by_cognito_sub(db, get_current_user_id(claims))
        db_business_plan = create_business_plan(db, metadata, user_id=user_id)

        return {
            "success": True,
            "message": "File metadata saved successfully",
            "file_id": db_business_plan.id,
            "user_id": user_id,
            "status": "pending",
            "created_at": db_business_plan.created_at.isoformat()
            if db_business_plan.created_at
            else None,
            "updated_at": db_business_plan.updated_at.isoformat()
            if db_business_plan.updated_at
            else None,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error saving business plan metadata: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error saving file metadata: {str(e)}"
        )


#####################################
# End of Upload-related endpoints   #
#####################################

#####################################
# Start of Search-related endpoints #
#####################################


@files.get("/search", response_model=dict)
def search_my_files(
    keywords: Optional[str] = Query(None, description="Keyword for searching files"),
    status_filter: Optional[str] = Query(
        None, description="상태 필터 (pending, processing, completed, failed)"
    ),
    limit: int = Query(50, ge=1, le=100, description="Number of files to search for"),
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
):
    """Search user's files"""
    user_id = get_current_user_id(claims)

    query = db.query(BusinessPlan).filter(BusinessPlan.user_id == user_id)

    if keywords:
        query = query.filter(BusinessPlan.file_name.ilike(f"%{keywords}%"))

    if status_filter:
        if status_filter not in ["pending", "processing", "completed", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status filter"
            )
        query = query.filter(BusinessPlan.status == status_filter)

    _files = query.order_by(desc(BusinessPlan.created_at)).limit(limit).all()

    return {
        "success": True,
        "results": [serialize_business_plan(_file) for _file in _files],
    }


@files.get("/", response_model=dict)
def get_my_files(
    limit: int = Query(50, ge=1, le=100, description="조회할 파일 수"),
    offset: int = Query(0, ge=0, description="시작 위치 (페이지네이션)"),
    db: Session = Depends(get_db),
    #claims: Dict[str, Any] = Depends(get_claims),
):
    """Search all files uploaded by the user (최신순)"""
    #user_id = get_current_user_id(claims)
    user_id = "6428ad7c-5021-703c-630a-3a9ecbb3407b"  # 임시 하드코딩
    _files = (
        db.query(BusinessPlan)
        .filter(BusinessPlan.user_id == user_id)
        .order_by(desc(BusinessPlan.created_at))
        .limit(limit)
        .offset(offset)
        .all()
    )

    return {
        "success": True,
        "results": [serialize_business_plan(_file) for _file in _files],
    }


#####################################
# End of Search-related endpoints   #
#####################################


@files.delete("/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    #claims: Dict[str, Any] = Depends(require_scope("bizlenz/write")),
):
    """Delete file, both in S3 and DB"""
    #user_id = get_current_user_id(claims)
    user_id = "6428ad7c-5021-703c-630a-3a9ecbb3407b"  # 임시 하드코딩
    try:
        file = db.query(BusinessPlan).filter(BusinessPlan.id == file_id).first()

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        '''if file.user_id != user_id and not is_admin(claims):
            raise HTTPException(
                status_code=403,
                detail="Permission denied: You can only delete your own files",
            )'''

        if file.file_path:
            print(f"DEBUG - file.file_path: {file.file_path}")
            print(f"DEBUG - settings.s3_bucket_name: {settings.s3_bucket_name}")
            
            # S3 키 추출
            if "s3.amazonaws.com/" in file.file_path:
                s3_key = file.file_path.split("s3.amazonaws.com/")[-1]
            else:
                s3_key = file.file_path
            
            print(f"DEBUG - extracted s3_key: {s3_key}")
            
            try:
                response = s3_client.delete_object(Bucket=settings.s3_bucket_name, Key=s3_key)
                print(f"DEBUG - S3 delete successful: {response}")
            except Exception as s3_error:
                print(f"DEBUG - S3 delete failed: {s3_error}")
                raise s3_error

        db.delete(file)
        db.commit()

        return {
            "success": True,
            "message": "File deleted successfully",
            "deleted_file_id": file_id,
        }
    
    except (ClientError, BotoCoreError) as s3_error:
        db.rollback()
        print(f"S3 deletion failed: {s3_error}")
        raise HTTPException(
            status_code=500, detail="File deletion failed: S3 error occurred"
        )
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        print(f"Database deletion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


@files.get("/{file_id}/download", response_model=dict)
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
):
    """Download the file"""
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

        try:
            s3_key = _file.file_path.split(
                f"{settings.s3_bucket_name}.s3.amazonaws.com/"
            )[-1]
            presigned_url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.s3_bucket_name, "Key": s3_key},
                ExpiresIn=300,
            )

            return {
                "success": True,
                "file_id": file_id,
                "file_name": _file.file_name,
                "presigned_url": presigned_url,
            }

        except Exception as s3_error:
            print(f"S3 presigned URL generation failed: {s3_error}")
            raise HTTPException(
                status_code=500, detail="Failed to generate download URL"
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error preparing file download: {str(e)}"
        )


#####################################
# Start of Admin-related endpoints #
#####################################


@files.get("/admin/all", response_model=dict)
def get_all_files_admin(
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
    limit: int = Query(100, ge=1, le=500, description="조회할 파일 수"),
    offset: int = Query(0, ge=0, description="시작 위치"),
):
    """Get ALL files"""
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

        return {
            "success": True,
            "results": [
                {
                    "id": file.id,
                    "file_name": file.file_name,
                    "status": file.status,
                    "file_size": file.file_size,
                    "mime_type": file.mime_type,
                    "created_at": file.created_at.isoformat()
                    if file.created_at
                    else None,
                    "user_id": file.user_id,
                    "latest_job_id": file.latest_job_id,
                }
                for file in _files
            ],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving all files: {str(e)}"
        )


@files.get("/admin/search", response_model=dict)
def search_all_files_admin(
    keywords: Optional[str] = Query(None, description="Keyboard to search for"),
    user_id: Optional[str] = Query(None, description="Filter for a specific user id"),
    status_filter: Optional[str] = Query(
        None, description="Filter for a specific status"
    ),
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
    limit: int = Query(100, ge=1, le=500, description="Number of files to search for"),
):
    """Search ALL files"""
    if not is_admin(claims):
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        query = db.query(BusinessPlan)

        if keywords:
            query = query.filter(BusinessPlan.file_name.ilike(f"%{keywords}%"))

        if user_id:
            query = query.filter(BusinessPlan.user_id == user_id)

        if status_filter:
            if status_filter not in ["pending", "processing", "completed", "failed"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid status filter",
                )
            query = query.filter(BusinessPlan.status == status_filter)

        _files = query.order_by(desc(BusinessPlan.created_at)).limit(limit).all()

        return {
            "success": True,
            "results": [
                {
                    "id": file.id,
                    "file_name": file.file_name,
                    "status": file.status,
                    "file_size": file.file_size,
                    "mime_type": file.mime_type,
                    "created_at": file.created_at.isoformat()
                    if file.created_at
                    else None,
                    "user_id": file.user_id,
                    "latest_job_id": file.latest_job_id,
                }
                for file in _files
            ],
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching files: {str(e)}")