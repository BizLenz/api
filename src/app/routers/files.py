# src/app/routers/files.py
import os
from uuid import uuid4
import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from math import ceil

load_dotenv()

required_env_vars = [
    "AWS_REGION",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "S3_BUCKET",
]
missing = [v for v in required_env_vars if not os.getenv(v)]
if missing:
    pass

s3_client = boto3.client("s3", region_name=os.getenv("AWS_REGION"))
BUCKET = os.getenv("S3_BUCKET")

router = APIRouter()


class UploadReq(BaseModel):
    filename: str
    filetype: str

    @field_validator("filetype")  # ← 변경
    @classmethod
    def validate_type(cls, v: str) -> str:
        allow = {"pdf", "png", "jpg", "jpeg"}
        if v.lower() not in allow:
            raise ValueError("unsupported filetype")
        return v


@router.post("/upload")
def upload_file(req: UploadReq):
    key = f"{uuid4()}.{req.filetype}"
    try:
        url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": BUCKET,
                "Key": key,
                "ContentType": f"application/{req.filetype}",
            },
            ExpiresIn=3600,
        )
        return {"upload_url": url, "file_url": f"s3://{BUCKET}/{key}"}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/select")
def select_files(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    resp = s3_client.list_objects_v2(Bucket=BUCKET)
    contents = resp.get("Contents", [])
    items = [{"file_name": c["Key"], "size": c.get("Size", 0)} for c in contents]

    start, end = (page - 1) * limit, (page - 1) * limit + limit
    paged = items[start:end]
    total = len(items)

    return {
        "data": paged,
        "pagination": {
            "total_files": total,
            "current_page": page,
            "limit": limit,
            "pages": ceil(total / limit) if limit else 0,
        },
    }


@router.get("/search")
def search_files(keywords: str, extension: str | None = None):
    resp = s3_client.list_objects_v2(Bucket=BUCKET)
    items = resp.get("Contents", [])

    kw = keywords.lower()
    ext = None if extension is None else extension.lower().lstrip(".")
    matched = []
    for c in items:
        key = c["Key"]
        size = c.get("Size", 0)
        k = key.lower()
        if kw in k and (ext is None or k.endswith(f".{ext}")):
            matched.append({"file_name": key, "size": size})  # ← size 포함

    return matched
