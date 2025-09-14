# api/src/app/routers/files.py
# uvicorn app.main:app --reload

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
    groups = claims.get("cognito:groups", [])
    return "admin" in groups or "administrators" in groups


def get_user_by_cognito_sub(db: Session, cognito_sub: str) -> str:
    """
    ERD 기준: users.id가 cognito_sub 값을 직접 저장
    cognito_sub를 그대로 user_id로 사용
    """
    get_or_create_user(db, cognito_sub=cognito_sub)
    return cognito_sub  # users.id = cognito_sub 값


# ============================================================================
# 파일 업로드 관련 API (ERD + API 명세서 기준)
# ============================================================================

@files.post("/upload", response_model=dict)
def upload(
    file_details: PresignedUrlRequest,
    claims: Dict[str, Any] = Depends(require_scope("bizlenz/write")),
):
    """
    PDF 파일 presigned URL 발급 엔드포인트 (API 명세서 기준)
    """
    try:
        cognito_sub = claims.get("sub")
        if not cognito_sub:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID (sub) not found in token claims.",
            )

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

        # API 명세서 기준 Response
        return {
            "user_id": cognito_sub,  # ERD: users.id = cognito_sub 값
            "file_name": file_details.file_name,
            "mime_type": file_details.mime_type,
            "file_size": file_details.file_size,
            "success": True,
            "message": "Presigned URL generated successfully",
            "presigned_url": url,
        }
    except (ClientError, BotoCoreError, Exception) as err:
        raise to_http_exception(err)


@files.post("/upload/metadata", response_model=dict)
def save_file_metadata(
    metadata: FileMetadataSaveRequest,
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(require_scope("bizlenz/write")),
):
    """
    클라이언트가 S3 업로드 후 호출하는 메타데이터 저장 API (ERD 기준)
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

        # ERD 기준: users.id = cognito_sub 값
        user_id = get_user_by_cognito_sub(db, cognito_sub)
        
        # business_plans 테이블에 저장
        db_business_plan = create_business_plan(db, metadata, user_id=user_id)

        # API 명세서 기준 Response
        return {
            "success": True,
            "message": "File metadata saved successfully",
            "file_id": db_business_plan.id,
            "user_id": user_id,  # cognito_sub 값
            "status": "pending",
            "created_at": db_business_plan.created_at.isoformat() if db_business_plan.created_at else None,
            "updated_at": db_business_plan.updated_at.isoformat() if db_business_plan.updated_at else None,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error saving business plan metadata: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error saving file metadata: {str(e)}"
        )


# ============================================================================
# 파일 검색 API (API 명세서 기준)
# ============================================================================

@files.get("/search", response_model=dict)
def search_my_files(
    keywords: Optional[str] = Query(None, description="파일명 검색 키워드"),
    status_filter: Optional[str] = Query(None, description="상태 필터 (pending, processing, completed, failed)"),
    limit: int = Query(50, ge=1, le=100, description="조회할 파일 수"),
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
):
    """
    내 파일 검색 (RDS 기반, API 명세서 기준)
    """
    cognito_sub = claims.get("sub")
    if not cognito_sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found in token claims"
        )

    # ERD 기준: business_plans.user_id = cognito_sub
    query = db.query(BusinessPlan).filter(BusinessPlan.user_id == cognito_sub)

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

    # API 명세서 기준 Response
    return {
        "success": True,
        "results": [
            {
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
            for file in files
        ]
    }


# ============================================================================
# 파일 삭제 API (ERD + API 명세서 기준)
# ============================================================================

@files.delete("/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(require_scope("bizlenz/write")),
):
    """
    파일 삭제 (DB ID 기반, S3 + DB 동시 삭제)
    """
    cognito_sub = claims.get("sub")
    if not cognito_sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found in token claims"
        )

    try:
        # 파일 조회 (ERD 기준: user_id = cognito_sub)
        file = db.query(BusinessPlan).filter(BusinessPlan.id == file_id).first()
        
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        # 권한 확인: 본인 파일이거나 관리자여야 함
        if file.user_id != cognito_sub and not is_admin(claims):
            raise HTTPException(
                status_code=403, 
                detail="Permission denied: You can only delete your own files"
            )

        # S3에서 파일 삭제 먼저 수행
        if file.file_path:
            s3_key = file.file_path.split(f"{settings.s3_bucket_name}.s3.amazonaws.com/")[-1]
            s3_client.delete_object(Bucket=settings.s3_bucket_name, Key=s3_key)

        # S3 삭제 성공 후에만 DB에서 파일 레코드 삭제
        # CASCADE로 관련 analysis_jobs, analysis_results도 삭제됨
        db.delete(file)
        db.commit()

        # API 명세서 기준 Response
        return {
            "success": True,
            "message": "File deleted successfully",
            "deleted_file_id": file_id
        }

    except (ClientError, BotoCoreError) as s3_error:
        db.rollback()
        print(f"S3 deletion failed: {s3_error}")
        raise HTTPException(
            status_code=500, 
            detail="File deletion failed: S3 error occurred"
        )
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        print(f"Database deletion failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error deleting file: {str(e)}"
        )


# ============================================================================
# 파일 다운로드 API (API 명세서 기준)
# ============================================================================

@files.get("/{file_id}/download", response_model=dict)
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
):
    """
    사업계획서 다운로드 (API 명세서 기준)
    """
    cognito_sub = claims.get("sub")
    if not cognito_sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found in token claims"
        )

    try:
        # ERD 기준: business_plans.user_id = cognito_sub
        file = db.query(BusinessPlan).filter(
            BusinessPlan.id == file_id,
            BusinessPlan.user_id == cognito_sub
        ).first()

        if not file:
            raise HTTPException(
                status_code=404,
                detail="File not found or access denied"
            )

        # S3에서 다운로드용 presigned URL 생성
        if not file.file_path:
            raise HTTPException(
                status_code=404,
                detail="File path not found"
            )

        try:
            # file_path에서 S3 key 추출
            s3_key = file.file_path.split(f"{settings.s3_bucket_name}.s3.amazonaws.com/")[-1]
            
            # 다운로드용 presigned URL 생성 (GET 방식)
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.s3_bucket_name, 'Key': s3_key},
                ExpiresIn=300  # 5분
            )

            # API 명세서 기준 Response
            return {
                "success": True,
                "file_id": file_id,
                "file_name": file.file_name,
                "presigned_url": presigned_url
            }

        except Exception as s3_error:
            print(f"S3 presigned URL generation failed: {s3_error}")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate download URL"
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error preparing file download: {str(e)}"
        )


# ============================================================================
# 관리자용 API (MVP 이후 구현 예정, 현재는 유지만)
# ============================================================================

@files.get("/admin/all", response_model=dict)
def get_all_files_admin(
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
    limit: int = Query(100, ge=1, le=500, description="조회할 파일 수"),
    offset: int = Query(0, ge=0, description="시작 위치"),
):
    """
    전체 파일 조회 (관리자만) - MVP 이후 구현 예정
    """
    if not is_admin(claims):
        raise HTTPException(
            status_code=403, 
            detail="Admin access required"
        )

    try:
        files = (
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
                    "created_at": file.created_at.isoformat() if file.created_at else None,
                    "user_id": file.user_id,  # cognito_sub 값
                    "latest_job_id": file.latest_job_id,
                }
                for file in files
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving all files: {str(e)}"
        )


@files.get("/admin/search", response_model=dict)
def search_all_files_admin(
    keywords: Optional[str] = Query(None, description="파일명 검색 키워드"),
    user_id: Optional[str] = Query(None, description="특정 사용자 ID로 필터"),
    status_filter: Optional[str] = Query(None, description="상태 필터"),
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
    limit: int = Query(100, ge=1, le=500, description="조회할 파일 수"),
):
    """
    전체 파일 검색 (관리자만) - MVP 이후 구현 예정
    """
    if not is_admin(claims):
        raise HTTPException(
            status_code=403, 
            detail="Admin access required"
        )

    try:
        query = db.query(BusinessPlan)

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

        return {
            "success": True,
            "results": [
                {
                    "id": file.id,
                    "file_name": file.file_name,
                    "status": file.status,
                    "file_size": file.file_size,
                    "mime_type": file.mime_type,
                    "created_at": file.created_at.isoformat() if file.created_at else None,
                    "user_id": file.user_id,  # cognito_sub 값
                    "latest_job_id": file.latest_job_id,
                }
                for file in files
            ]
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error searching files: {str(e)}"
        )