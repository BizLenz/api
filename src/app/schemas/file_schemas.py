from pydantic import BaseModel, Field, field_validator
from typing import Optional
from app.core.config import other_settings
from datetime import datetime
import re


# --- POST /files/upload endpoint (presigned URL generation) ---
class PresignedUrlRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="Ignored, extracted from JWT")
    file_name: str = Field(..., description="File Name")
    mime_type: str = Field(..., max_length=100, description="MIME Type")
    file_size: int = Field(..., gt=0, description="Size of the file in bytes")
    description: Optional[str] = Field(
        None, max_length=500, description="Description of the file"
    )

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v):
        if not v or v.isspace():
            raise ValueError("File name is a must.")
        forbidden_chars = re.compile(r'[\\/:*?"<>|]')
        if forbidden_chars.search(v):
            raise ValueError(
                'File name contains forbidden characters(\\ / : * ? " < > |).'
            )
        if not v.lower().endswith(".pdf"):
            raise ValueError("File name must end with .pdf extension.")
        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }
        name_part = v.rsplit(".", 1)[0].upper()
        if name_part in reserved_names:
            raise ValueError(f"File name contains reserved name: {name_part}")
        if any(ord(c) < 32 or ord(c) == 127 for c in v):
            raise ValueError("File name contains ASCII control characters (0-31, 127).")
        return v

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v):
        allowed_mime_types = ["application/pdf"]
        if v.lower() not in allowed_mime_types:
            raise ValueError(
                f"File type is not allowed, allowed types: {', '.join(allowed_mime_types)}"
            )
        return v.lower()

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v):
        max_size = other_settings.max_Size
        if v > max_size:
            max_size_mb = max_size / (1024 * 1024)
            raise ValueError(f"Size of the file cannot exceed {max_size_mb}MB.")
        if v <= 0:
            raise ValueError("File size must be bigger than 0.")
        return v

    class Config:
        schema_extra = {
            "example": {
                "user_id": None,
                "file_name": "My_Business_Plan.pdf",
                "mime_type": "application/pdf",
                "file_size": 2048000,
                "description": "Annual business plan for Q3",
            }
        }
        allow_population_by_field_name = True


# --- POST /files/upload/metadata endpoint (metadata saving) ---
class FileMetadataSaveRequest(BaseModel):
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
    def validate_file_name(cls, v):
        if not v or v.isspace():
            raise ValueError("File name is a must.")
        forbidden_chars = re.compile(r'[\\/:*?"<>|]')
        if forbidden_chars.search(v):
            raise ValueError(
                'File name contains forbidden characters(\\ / : * ? " < > |).'
            )
        if not v.lower().endswith(".pdf"):
            raise ValueError("File name must end with .pdf extension.")
        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }
        name_part = v.rsplit(".", 1)[0].upper()
        if name_part in reserved_names:
            raise ValueError(f"File name contains reserved name: {name_part}")
        if any(ord(c) < 32 or ord(c) == 127 for c in v):
            raise ValueError("File name contains ASCII control characters (0-31, 127).")
        return v

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v):
        allowed_mime_types = ["application/pdf"]
        if v.lower() not in allowed_mime_types:
            raise ValueError(
                f"MIME type is not allowed, allowed types: {', '.join(allowed_mime_types)}"
            )
        return v.lower()

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v):
        max_size = other_settings.max_Size
        if v > max_size:
            raise ValueError(f"File size cannot exceed {max_size / (1024 * 1024)}MB.")
        if v <= 0:
            raise ValueError("File size must be bigger than 0.")
        return v

    @field_validator("s3_key")
    @classmethod
    def validate_s3_key(cls, v):
        if not v:
            raise ValueError("S3 key is a must.")
        return v

    @field_validator("s3_file_url")
    @classmethod
    def validate_s3_file_url(cls, v):
        if not v:
            raise ValueError("S3 file URL is a must.")
        return v

    class Config:
        schema_extra = {
            "example": {
                "user_id": None,
                "file_name": "My_Business_Plan.pdf",
                "mime_type": "application/pdf",
                "file_size": 2048000,
                "description": "Annual business plan for Q3",
                "s3_key": "uploads/uuid_My_Business_Plan.pdf",
                "s3_file_url": "https://your-bucket.s3.amazonaws.com/uploads/uuid_My_Business_Plan.pdf",
            }
        }
        allow_population_by_field_name = True


class FileUploadRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="Ignored, extracted from JWT")
    file_name: str = Field(..., description="File name")
    mime_type: str = Field(..., max_length=100, description="MIME type")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    description: Optional[str] = Field(
        None, max_length=500, description="Description of the file"
    )

    @field_validator("file_name")
    def validate_file_name(cls, v):
        """
        Check if the file name is valid
        - Check for invalid characters
        - Check for reserved names
        - Check for PDF extension
        """
        if not v or v.isspace():
            raise ValueError("File name is a must.")

        invalid_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        if any(char in v for char in invalid_chars):
            raise ValueError(
                f"File name contains invalid characters: {', '.join(invalid_chars)}"
            )

        if not v.lower().endswith(".pdf"):
            raise ValueError("File name must end with .pdf extension.")
        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }
        name_part = v.split(".")[0].upper()
        if name_part in reserved_names:
            raise ValueError(f"File name contains reserved name: {name_part}")

        if any(ord(c) < 32 or ord(c) == 127 for c in v):
            raise ValueError("File name contains ASCII control characters (0-31, 127).")

        # Check for any AWS S3 related special characters
        special_chars = set("&$@=;/:+ ,?")
        if any(char in special_chars for char in v):
            raise ValueError(
                f"File name contains special characters: {' '.join(special_chars)}"
            )
        return v

    @field_validator("mime_type")
    def validate_mime_type(cls, v):
        """
        Check if the MIME type is valid
        - Only PDF is allowed
        """
        allowed_mime_types = ["application/pdf"]
        if v.lower() not in allowed_mime_types:
            raise ValueError(
                f"MIME type is not allowed, allowed types: {', '.join(allowed_mime_types)}"
            )
        return v.lower()

    @field_validator("file_size")
    def validate_file_size(cls, v):
        """
        Check for file size
        """
        # 500MB at maximum
        max_size = other_settings.max_Size
        if v > max_size:
            max_size_mb = max_size / (1024 * 1024)
            raise ValueError(f"File size cannot exceed {max_size_mb}MB.")
        if v <= 0:
            raise ValueError("File size must be bigger than 0.")
        return v

    class Config:
        schema_extra = {
            "example": {
                "user_id": None,
                "file_name": "example.pdf",
                "mime_type": "application/pdf",
                "file_size": 204800,
                "description": "Sample PDF file for upload",
            }
        }
        allow_population_by_field_name = True


class FileUploadResponse(BaseModel):
    """
    Model for file upload response
    """

    id: int = Field(..., description="File ID")
    user_id: Optional[str] = Field(None, description="Ignored, extracted from JWT")
    file_name: str = Field(..., description="File Name")
    file_path: str = Field(..., description="S3 URL")
    mime_type: str = Field(..., description="MIME Type")
    file_size: int = Field(..., description="File size in bytes")
    created_at: datetime = Field(..., description="File created at")
    updated_at: datetime = Field(..., description="File updated at")

    # Additional metadata fields
    success: bool = Field(..., description="Upload success")
    message: Optional[str] = Field(None, description="Additional message")
    presigned_url: Optional[str] = Field(None, description="S3 presigned URL")

    class Config:
        orm_mode = True
        schema_extra = {
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
        }


class FileListResponse(BaseModel):
    """
    Pydantic model for file list response
    """

    id: int
    file_name: str
    file_size: int
    mime_type: str
    created_at: datetime

    class Config:
        orm_mode = True


class FileUploadError(BaseModel):
    """
    Pydantic model for file upload error response
    """

    success: bool = Field(False, description="Upload error")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Error details")

    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error_code": "FILE_SIZE_EXCEEDED",
                "error_message": "File size exceeded the maximum allowed size.",
                "details": {"max_size": "50MB", "uploaded_size": "75MB"},
            }
        }
