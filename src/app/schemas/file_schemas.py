from datetime import datetime
from typing import Optional
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings


# ---------------------------------------------------------------------------
# Shared validator helpers
# ---------------------------------------------------------------------------

ALLOWED_MIME_TYPES = ["application/pdf"]

_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_FORBIDDEN_CHARS = re.compile(r'[\\/:*?"<>|]')


def _validate_pdf_file_name(v: str) -> str:
    if not v or v.isspace():
        raise ValueError("File name is a must.")
    if _FORBIDDEN_CHARS.search(v):
        raise ValueError('File name contains forbidden characters(\\ / : * ? " < > |).')
    if not v.lower().endswith(".pdf"):
        raise ValueError("File name must end with .pdf extension.")
    name_part = v.rsplit(".", 1)[0].upper()
    if name_part in _RESERVED_NAMES:
        raise ValueError(f"File name contains reserved name: {name_part}")
    if any(ord(c) < 32 or ord(c) == 127 for c in v):
        raise ValueError("File name contains ASCII control characters (0-31, 127).")
    return v


def _validate_mime_type(v: str) -> str:
    if v.lower() not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"File type is not allowed, allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
        )
    return v.lower()


def _validate_file_size(v: int) -> int:
    max_size = settings.s3_max_file_size
    if v > max_size:
        max_size_mb = max_size / (1024 * 1024)
        raise ValueError(f"Size of the file cannot exceed {max_size_mb}MB.")
    if v <= 0:
        raise ValueError("File size must be bigger than 0.")
    return v


# ---------------------------------------------------------------------------
# POST /files/upload (presigned URL generation)
# ---------------------------------------------------------------------------


class PresignedUrlRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "user_id": None,
                "file_name": "business_plan.pdf",
                "mime_type": "application/pdf",
                "file_size": 2048000,
                "description": "Annual business plan for Q1",
            }
        },
    )

    user_id: Optional[str] = Field(None, description="Ignored, extracted from JWT")
    file_name: str = Field(..., description="File Name")
    mime_type: str = Field(..., max_length=100, description="MIME Type")
    file_size: int = Field(..., gt=0, description="Size of the file in bytes")
    description: Optional[str] = Field(
        None, max_length=500, description="Description of the file"
    )

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        return _validate_pdf_file_name(v)

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        return _validate_mime_type(v)

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        return _validate_file_size(v)


# ---------------------------------------------------------------------------
# POST /files/upload/metadata (metadata saving)
# ---------------------------------------------------------------------------


class FileMetadataSaveRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "user_id": None,
                "file_name": "business_plan.pdf",
                "mime_type": "application/pdf",
                "file_size": 2048000,
                "description": "Annual business plan for Q1",
                "s3_key": "uploads/uuid_business_plan.pdf",
                "s3_file_url": "https://your-bucket.s3.amazonaws.com/uploads/uuid_business_plan.pdf",
            }
        },
    )

    user_id: Optional[str] = Field(None, description="Ignored, extracted from JWT")
    file_name: str = Field(..., max_length=255, description="File Name")
    mime_type: str = Field(..., max_length=100, description="MIME Type")
    file_size: int = Field(..., gt=0, description="Size of the file in bytes")
    description: Optional[str] = Field(
        None, max_length=500, description="Description of the file"
    )
    s3_key: str = Field(..., description="S3 object key")
    s3_file_url: str = Field(..., description="Full URL to the S3 object")

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        return _validate_pdf_file_name(v)

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        return _validate_mime_type(v)

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        return _validate_file_size(v)

    @field_validator("s3_key")
    @classmethod
    def validate_s3_key(cls, v: str) -> str:
        if not v:
            raise ValueError("S3 key is a must.")
        return v

    @field_validator("s3_file_url")
    @classmethod
    def validate_s3_file_url(cls, v: str) -> str:
        if not v:
            raise ValueError("S3 file URL is a must.")
        return v


# ---------------------------------------------------------------------------
# FileUploadRequest (direct multipart upload)
# ---------------------------------------------------------------------------

_S3_SPECIAL_CHARS = set("&$@=;/:+ ,?")


class FileUploadRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "user_id": None,
                "file_name": "example.pdf",
                "mime_type": "application/pdf",
                "file_size": 204800,
                "description": "Sample PDF file for upload",
            }
        },
    )

    user_id: Optional[str] = Field(None, description="Ignored, extracted from JWT")
    file_name: str = Field(..., description="File name")
    mime_type: str = Field(..., max_length=100, description="MIME type")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    description: Optional[str] = Field(
        None, max_length=500, description="Description of the file"
    )

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        # Base validation shared with other schemas
        _validate_pdf_file_name(v)
        # S3 object-key special characters
        if any(char in _S3_SPECIAL_CHARS for char in v):
            raise ValueError(
                f"File name contains special characters: {' '.join(sorted(_S3_SPECIAL_CHARS))}"
            )
        return v

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        return _validate_mime_type(v)

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        return _validate_file_size(v)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class FileUploadResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": None,
                "file_name": "example.pdf",
                "file_path": "uploads/example.pdf",
                "mime_type": "application/pdf",
                "file_size": 204800,
                "created_at": "2023-10-01T12:00:00Z",
                "updated_at": "2023-10-01T12:00:00Z",
                "success": True,
                "message": "File uploaded successfully",
                "presigned_url": "https://s3.amazonaws.com/bucket/uploads/example.pdf",
            }
        },
    )

    id: int = Field(..., description="File ID")
    user_id: Optional[str] = Field(None, description="Ignored, extracted from JWT")
    file_name: str = Field(..., description="File Name")
    file_path: str = Field(..., description="S3 URL")
    mime_type: str = Field(..., description="MIME Type")
    file_size: int = Field(..., description="File size in bytes")
    created_at: datetime = Field(..., description="File created at")
    updated_at: datetime = Field(..., description="File updated at")

    success: bool = Field(..., description="Upload success")
    message: Optional[str] = Field(None, description="Additional message")
    presigned_url: Optional[str] = Field(None, description="S3 presigned URL")


class FileListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    file_size: int
    mime_type: str
    created_at: datetime


class FileUploadError(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "error_code": "FILE_SIZE_EXCEEDED",
                "error_message": "File size exceeded the maximum allowed size.",
                "details": {"max_size": "50MB", "uploaded_size": "75MB"},
            }
        }
    )

    success: bool = Field(False, description="Upload error")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Error details")
