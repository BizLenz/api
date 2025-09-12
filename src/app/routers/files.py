from fastapi import APIRouter, HTTPException, Query, Depends, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from botocore.exceptions import ClientError, BotoCoreError
from uuid import uuid4
from app.crud.file_metadata import create_business_plan
from app.core.config import settings
from app.database import get_db
from app.core.security import require_scope, get_claims
from app.core.exceptions import to_http_exception
from app.crud.user import get_or_create_user
import boto3

from app.schemas.file_schemas import PresignedUrlRequest, FileMetadataSaveRequest

# 라우터: 기본적으로 read 권한 검사(값은 주입되지 않음. 주입하려면 각 엔드포인트 파라미터로 Depends 사용)
files = APIRouter(dependencies=[Depends(require_scope("bizlenz/read"))])

# S3 클라이언트
s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
)


# PDF Presigned URL 발급 엔드포인트
@files.post("/upload", response_model=dict)
def upload(
    file_details: PresignedUrlRequest,
    claims: Dict[str, Any] = Depends(require_scope("bizlenz/write")),  # 쓰기 권한
):
    """
    PDF 파일 presigned URL 발급 엔드포인트
    - presigned URL로 S3에 파일 업로드 (PUT 방식)
    - 환경설정 정보 기반 버킷/경로 설정
    - 예외 발생 시 FastAPI 오류 반환
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
    claims: Dict[str, Any] = Depends(require_scope("bizlenz/write")),  # 쓰기 권한
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
                detail="User ID (sub) not found in token claims. Cannot save metadata without user.",
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


# S3 파일 삭제 엔드포인트
@files.delete("/{key:path}")
async def delete_file(
    key: str,
    claims: Dict[str, Any] = Depends(require_scope("bizlenz/write")),  # 쓰기 권한
):
    """
    S3에서 파일 삭제 엔드포인트
    - key: S3 내 파일 경로 (예: uploads/example.pdf)
    """
    try:
        s3_client.delete_object(Bucket=settings.s3_bucket_name, Key=key)
        return {"message": "File deleted successfully"}
    except (ClientError, BotoCoreError, Exception) as e:
        raise to_http_exception(e)


# S3 파일 검색 엔드포인트
@files.get("/search")
async def search_files(
    keywords: Optional[str] = Query(None, description="파일 이름 검색 키워드"),
    extension: Optional[str] = Query(None, description="파일 확장자 (예: pdf)"),
    claims: Dict[str, Any] = Depends(
        get_claims
    ),  # 라우터 레벨 read 검사 + 실제 claims 접근
):
    """
    파일 이름 및 확장자 기반 검색 엔드포인트
    - keywords: 파일명에 포함될 키워드 (optional)
    - extension: 검색할 파일 확장자 (optional)
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
            # Turn into user-friendly name (remove UUID)
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


# S3 파일 목록 페이지네이션 조회 엔드포인트
@files.get("/select")
async def select_files(
    limit: int = Query(
        10, ge=1, le=1000, description="페이지당 조회할 객체 수 (1~1000)"
    ),
    continuation_token: Optional[str] = Query(
        None, description="다음 페이지 조회를 위한 ContinuationToken"
    ),
    claims: Dict[str, Any] = Depends(
        get_claims
    ),  # 라우터 레벨 read 검사 + 실제 claims 접근
) -> Dict:
    """
    S3 버킷 내 객체를 커서 기반 페이지네이션 방식으로 조회합니다.
    - limit: 한 페이지당 객체 수
    - continuation_token: 이전 요청에서 받은 NextContinuationToken
    """
    try:
        # paginator 사용 버전 유지
        paginator = s3_client.get_paginator("list_objects_v2")
        paginate_params = {
            "Bucket": settings.s3_bucket_name,
            "PaginationConfig": {"PageSize": limit},
        }
        if continuation_token:
            paginate_params["PaginationConfig"]["StartingToken"] = continuation_token

        page_iterator = paginator.paginate(**paginate_params)

        page = next(page_iterator, None)
        if not page or "Contents" not in page:
            return {"data": [], "pagination": {"next_token": None, "count": 0}}

        files_list = [
            {
                "key": obj["Key"],
                "last_modified": obj["LastModified"].isoformat(),
                "size": obj["Size"],
            }
            for obj in page["Contents"]
        ]
        next_token = page.get("NextContinuationToken")
        return {
            "data": files_list,
            "pagination": {"next_token": next_token, "count": len(files_list)},
        }
    except (ClientError, BotoCoreError, Exception) as e:
        raise to_http_exception(e)