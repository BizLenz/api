from fastapi import APIRouter, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict
from botocore.exceptions import ClientError
from uuid import uuid4
from app.schemas.file_schemas import FileUploadRequest, FileUploadResponse
from app.core.config import settings   # 환경설정 객체 import
import boto3

# FastAPI 라우터 객체 생성
files = APIRouter()

# CORS 설정
origins = [
    "http://localhost:3000",  # 로컬 개발 환경 허용
]


# 환경설정 정보로 S3 클라이언트를 생성
s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region
)

# S3 관련 오류 처리 함수
def type_s3_exception(e: Exception):
    if isinstance(e, ClientError):
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        if error_code in ["NoSuchKey", "NotFound"]:
            raise HTTPException(status_code=404, detail=error_message)
        elif error_code == "AccessDenied":
            raise HTTPException(status_code=403, detail=error_message)
        elif error_code == "InvalidRequest":
            raise HTTPException(status_code=400, detail=error_message)
        else:
            raise HTTPException(status_code=500, detail=error_message)
    else:
        raise HTTPException(status_code=500, detail=str(e))

# PDF Presigned URL 발급 엔드포인트
@files.post("/upload", response_model=dict)
async def upload_file(file: FileUploadRequest):
    """
    PDF 파일 presigned URL 발급 엔드포인트
    - presigned URL로 S3에 파일 업로드 (PUT 방식)
    - 환경설정 정보 기반 버킷/경로 설정
    - 예외 발생 시 FastAPI 오류 반환
    """
    try:
        key = f"{settings.s3_upload_folder}/{uuid4()}_{file.file_name}"  # config에서 폴더명 불러옴
        url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.s3_bucket_name,
                'Key': key,
                'ContentType': file.mime_type
            },
            ExpiresIn=300  # 5분
        )
        return {
            "upload_url": url,
            "file_url": f"https://{settings.s3_bucket_name}.s3.amazonaws.com/{key}"
        }
    except Exception as e:
        raise type_s3_exception(e)

# S3 파일 삭제 엔드포인트
@files.delete("/{key:path}")
async def delete_file(key: str):
    """
    S3에서 파일 삭제 엔드포인트
    - key: S3 내 파일 경로 (예: uploads/example.pdf)
    - 환경설정의 버킷 정보 활용
    - 예외 시 FastAPI 오류 메시지 반환
    """
    try:
        s3_client.delete_object(
            Bucket=settings.s3_bucket_name,
            Key=key
        )
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise type_s3_exception(e)

# S3 파일 검색 엔드포인트
@files.get("/search")
async def search_files(
    keywords: Optional[str] = Query(None, description="파일 이름 검색 키워드"),
    extension: Optional[str] = Query(None, description="파일 확장자 (예: pdf)")
):
    """
    파일 이름 및 확장자 기반 검색 엔드포인트
    - keywords: 파일명에 포함될 키워드 (optional)
    - extension: 검색할 파일 확장자 (optional)
    """
    try:
        response = s3_client.list_objects_v2(Bucket=settings.s3_bucket_name)
        if 'Contents' not in response:
            return []

        files = response['Contents']
        result = []
        for obj in files:
            file_name = obj['Key']
            # 키워드 필터
            if keywords and keywords.lower() not in file_name.lower():
                continue
            # 확장자 필터링 (예: .pdf)
            if extension:
                normalized_extension = f".{extension.lower().lstrip('.')}"
                if not file_name.endswith(normalized_extension):
                    continue
            result.append({
                "file_name": file_name,
                "last_modified": obj['LastModified'].isoformat(),
                "size": obj['Size']
            })
        return result
    except Exception as e:
        raise type_s3_exception(e)

# S3 파일 목록 페이지네이션 조회 엔드포인트
@files.get("/select")
def select_files(
    page: int = Query(1, ge=1),   # 페이지 번호, 1부터 시작
    limit: int = Query(10, ge=1)  # 페이지당 항목 수
) -> Dict:
    """
    S3 파일 목록을 페이지네이션하여 반환하는 엔드포인트
    - page: 페이지 번호
    - limit: 한 페이지당 파일 개수
    """
    try:
        response = s3_client.list_objects_v2(Bucket=settings.s3_bucket_name)
        contents = response.get("Contents", [])
        total_files = len(contents)
        total_pages = (total_files + limit - 1) // limit
        offset = (page - 1) * limit
        page_items = contents[offset: offset + limit]
        files_list = [
            {
                "key": obj['Key'],
                "last_modified": obj['LastModified'].isoformat(),
                "size": obj['Size']
            }
            for obj in page_items
        ]
        return {
            "data": files_list,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_files": total_files,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
    except Exception as e:
        raise type_s3_exception(e)
