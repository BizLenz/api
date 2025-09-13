# api/src/app/routers/files.py
#uvicorn app.main:app --reload

from fastapi import APIRouter, HTTPException, Query, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, Dict, Any, List
from botocore.exceptions import ClientError, BotoCoreError
from uuid import uuid4
from app.crud.file_metadata import create_business_plan
from app.core.config import settings
from app.database import get_db
from app.core.security import require_scope, get_claims
from app.core.exceptions import to_http_exception
from app.crud.user import get_or_create_user
from app.models import BusinessPlan, User
import boto3

from app.schemas.file_schemas import PresignedUrlRequest, FileMetadataSaveRequest

# 라우터: 기본적으로 read 권한 검사
files = APIRouter(dependencies=[Depends(require_scope("bizlenz/read"))])

# S3 클라이언트
s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
)


def is_admin(claims: Dict[str, Any]) -> bool:
    """관리자 권한 확인"""
    # Cognito groups에서 admin 그룹 확인
    groups = claims.get("cognito:groups", [])
    return "admin" in groups or "administrators" in groups


# ============================================================================
# 파일 업로드 관련 API (기존 유지)
# ============================================================================

@files.post("/upload", response_model=dict)
def upload(
    file_details: PresignedUrlRequest,
    claims: Dict[str, Any] = Depends(require_scope("bizlenz/write")),
):
    """
    PDF 파일 presigned URL 발급 엔드포인트
    """
    try:
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
            ExpiresIn=300,  # 5 min
        )

        return {
            "upload_url": url,
            "file_url": f"https://{settings.s3_bucket_name}.s3.amazonaws.com/{s3_full_key}",
            "key": s3_full_key,
        }
    except (ClientError, BotoCoreError, Exception) as err:
        raise to_http_exception(err)

# RDS 파일 메타데이터 저장 엔드포인트
@files.post("/upload/metadata", response_model=dict)
def save_file_metadata(
    metadata: FileMetadataSaveRequest,
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(require_scope("bizlenz/write")),
):
    """
    클라이언트가 S3 업로드 후 호출하는 메타데이터 저장 API
    """
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

        cognito_sub = claims.get("sub")
        if not cognito_sub:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID (sub) not found in token claims.",
            )

        db_user = get_or_create_user(db, cognito_sub=cognito_sub)
        db_business_plan = create_business_plan(db, metadata, user_id=db_user.id)

        return {
            "message": "File metadata saved successfully",
            "file_id": db_business_plan.id,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error saving business plan metadata: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error saving file metadata: {str(e)}"
        )


# ============================================================================
# 사용자별 파일 조회/관리 API (새로 추가 - RDS 기반)
# ============================================================================

@files.get("", response_model=List[dict])
def get_my_files(
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
    limit: int = Query(50, ge=1, le=100, description="조회할 파일 수"),
    offset: int = Query(0, ge=0, description="시작 위치"),
):
    """
    내 파일 목록 조회 (RDS 기반)
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found in token claims"
        )

    try:
        files = (
            db.query(BusinessPlan)
            .filter(BusinessPlan.user_id == user_id)
            .order_by(desc(BusinessPlan.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

        return [
            {
                "id": file.id,
                "file_name": file.file_name,
                "status": file.status,
                "file_size": file.file_size,
                "mime_type": file.mime_type,
                "created_at": file.created_at.isoformat() if file.created_at else None,
                "updated_at": file.updated_at.isoformat() if file.updated_at else None,
                "latest_job_id": file.latest_job_id,
            }
            for file in files
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving files: {str(e)}"
        )


@files.get("/search", response_model=List[dict])
def search_my_files(
    keywords: Optional[str] = Query(None, description="파일명 검색 키워드"),
    status_filter: Optional[str] = Query(None, description="상태 필터 (pending, processing, completed, failed)"),
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
    limit: int = Query(50, ge=1, le=100, description="조회할 파일 수"),
):
    """
    내 파일 검색 (RDS 기반)
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found in token claims"
        )

    try:
        query = db.query(BusinessPlan).filter(BusinessPlan.user_id == user_id)

        if keywords:
            query = query.filter(BusinessPlan.file_name.ilike(f"%{keywords}%"))
        
        if status_filter:
            if status_filter not in ['pending', 'processing', 'completed', 'failed']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid status filter"
                )
            query = query.filter(BusinessPlan.status == status_filter)

        files = query.order_by(desc(BusinessPlan.created_at)).limit(limit).all()

        return [
            {
                "id": file.id,
                "file_name": file.file_name,
                "status": file.status,
                "file_size": file.file_size,
                "mime_type": file.mime_type,
                "created_at": file.created_at.isoformat() if file.created_at else None,
                "updated_at": file.updated_at.isoformat() if file.updated_at else None,
                "latest_job_id": file.latest_job_id,
            }
            for file in files
        ]
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error searching files: {str(e)}"
        )


@files.get("/{file_id}", response_model=dict)
def get_file_detail(
    file_id: int,
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
):
    """
    특정 파일 상세 정보 조회
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found in token claims"
        )

    try:
        file = (
            db.query(BusinessPlan)
            .filter(
                BusinessPlan.id == file_id,
                BusinessPlan.user_id == user_id
            )
            .first()
        )

        if not file:
            raise HTTPException(
                status_code=404, 
                detail="File not found or access denied"
            )

        return {
            "id": file.id,
            "file_name": file.file_name,
            "file_path": file.file_path,
            "status": file.status,
            "file_size": file.file_size,
            "mime_type": file.mime_type,
            "created_at": file.created_at.isoformat() if file.created_at else None,
            "updated_at": file.updated_at.isoformat() if file.updated_at else None,
            "latest_job_id": file.latest_job_id,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving file detail: {str(e)}"
        )


# ============================================================================
# 파일 삭제 API (S3 + DB 동시 삭제)
# ============================================================================

@files.delete("/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(require_scope("bizlenz/write")),
):
    """
    파일 삭제 (본인 파일 또는 관리자만 가능, S3 + DB 동시 삭제)
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found in token claims"
        )

    try:
        # 파일 조회
        file = db.query(BusinessPlan).filter(BusinessPlan.id == file_id).first()
        
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        # 권한 확인: 본인 파일이거나 관리자여야 함
        if file.user_id != user_id and not is_admin(claims):
            raise HTTPException(
                status_code=403, 
                detail="Permission denied: You can only delete your own files"
            )

        # S3에서 파일 삭제
        if file.file_path:
            try:
                # file_path에서 S3 key 추출 (S3 URL에서 key 부분만)
                s3_key = file.file_path.split(f"{settings.s3_bucket_name}.s3.amazonaws.com/")[-1]
                s3_client.delete_object(Bucket=settings.s3_bucket_name, Key=s3_key)
            except Exception as s3_error:
                print(f"S3 deletion failed: {s3_error}")
                # S3 삭제 실패해도 DB 삭제는 진행 (orphan 방지)

        # DB에서 파일 레코드 삭제 (CASCADE로 관련 analysis_jobs, analysis_results도 삭제됨)
        db.delete(file)
        db.commit()

        return {
            "message": "File deleted successfully",
            "deleted_file_id": file_id
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error deleting file: {str(e)}"
        )


# ============================================================================
# 관리자용 API (전체 파일 관리)
# ============================================================================

@files.get("/admin/all", response_model=List[dict])
def get_all_files_admin(
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
    limit: int = Query(100, ge=1, le=500, description="조회할 파일 수"),
    offset: int = Query(0, ge=0, description="시작 위치"),
):
    """
    전체 파일 조회 (관리자만)
    """
    if not is_admin(claims):
        raise HTTPException(
            status_code=403, 
            detail="Admin access required"
        )

    try:
        files = (
            db.query(BusinessPlan, User.id.label("user_cognito_sub"))
            .join(User, BusinessPlan.user_id == User.id)
            .order_by(desc(BusinessPlan.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

        return [
            {
                "id": file.BusinessPlan.id,
                "file_name": file.BusinessPlan.file_name,
                "status": file.BusinessPlan.status,
                "file_size": file.BusinessPlan.file_size,
                "mime_type": file.BusinessPlan.mime_type,
                "created_at": file.BusinessPlan.created_at.isoformat() if file.BusinessPlan.created_at else None,
                "user_id": file.user_cognito_sub,
                "latest_job_id": file.BusinessPlan.latest_job_id,
            }
            for file in files
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving all files: {str(e)}"
        )


@files.get("/admin/search", response_model=List[dict])
def search_all_files_admin(
    keywords: Optional[str] = Query(None, description="파일명 검색 키워드"),
    user_id: Optional[str] = Query(None, description="특정 사용자 ID로 필터"),
    status_filter: Optional[str] = Query(None, description="상태 필터"),
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
    limit: int = Query(100, ge=1, le=500, description="조회할 파일 수"),
):
    """
    전체 파일 검색 (관리자만)
    """
    if not is_admin(claims):
        raise HTTPException(
            status_code=403, 
            detail="Admin access required"
        )

    try:
        query = db.query(BusinessPlan, User.id.label("user_cognito_sub")).join(
            User, BusinessPlan.user_id == User.id
        )

        if keywords:
            query = query.filter(BusinessPlan.file_name.ilike(f"%{keywords}%"))
        
        if user_id:
            query = query.filter(BusinessPlan.user_id == user_id)
        
        if status_filter:
            if status_filter not in ['pending', 'processing', 'completed', 'failed']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid status filter"
                )
            query = query.filter(BusinessPlan.status == status_filter)

        files = query.order_by(desc(BusinessPlan.created_at)).limit(limit).all()

        return [
            {
                "id": file.BusinessPlan.id,
                "file_name": file.BusinessPlan.file_name,
                "status": file.BusinessPlan.status,
                "file_size": file.BusinessPlan.file_size,
                "mime_type": file.BusinessPlan.mime_type,
                "created_at": file.BusinessPlan.created_at.isoformat() if file.BusinessPlan.created_at else None,
                "user_id": file.user_cognito_sub,
                "latest_job_id": file.BusinessPlan.latest_job_id,
            }
            for file in files
        ]
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error searching files: {str(e)}"
        )


# ============================================================================
# 레거시 S3 직접 접근 API (하위 호환성, 사용 비권장)
# ============================================================================

@files.get("/legacy/s3-search")
async def legacy_search_s3_files(
    keywords: Optional[str] = Query(None, description="파일 이름 검색 키워드"),
    extension: Optional[str] = Query(None, description="파일 확장자 (예: pdf)"),
    claims: Dict[str, Any] = Depends(get_claims),
):
    """
    레거시: S3 직접 검색 (사용 비권장, 하위 호환성 목적)
    """
    try:
        response = s3_client.list_objects_v2(Bucket=settings.s3_bucket_name)
        if "Contents" not in response:
            return []

        res_files = response["Contents"]
        result: List[Dict[str, Any]] = []
        normalized_extension = (
            f".{extension.lower().lstrip('.')}" if extension else None
        )

        for obj in res_files:
            file_name = obj["Key"]
            if keywords and keywords.lower() not in file_name.lower():
                continue
            if normalized_extension and not file_name.lower().endswith(
                normalized_extension
            ):
                continue

            display_file_name = file_name
            parts = file_name.split("_", 1)
            if len(parts) > 1 and parts[0].isalnum() and "-" in parts[0]:
                display_file_name = parts[1]

            result.append(
                {
                    "file_name": display_file_name,
                    "last_modified": obj["LastModified"].isoformat(),
                    "size": obj["Size"],
                }
            )
        return result
    except (ClientError, BotoCoreError, Exception) as e:
        raise to_http_exception(e)