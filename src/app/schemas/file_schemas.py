from pydantic  import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from app.core.config import other_settings

class FileUploadRequest(BaseModel):

    # 파일 테이블 기반 정보 필드
    user_id: int = Field(..., description="사용자 ID")
    file_name: str = Field(..., description="업로드할 파일 이름")
    mime_type: str = Field(..., max_length=100, description="파일 MIME 타입")
    file_size: int = Field(..., gt=0, description="파일 크기 (바이트 단위)")
    description: Optional[str] = Field(None, max_length=500, description="파일 설명")

    @field_validator('file_name')
    def validate_file_name(cls,v):
        """
        파일명 유효성 검증
        - 빈 문자열 불허
        - S3 업로드 시 문제가 될 수 있는 특수문자 차단
        - PDF 확장자 필수
        """
        if not v or v.isspace():
            raise ValueError("파일 이름은 필수입니다.")

        #허용되지 않는 특수문자 체크
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any (char in v for char in invalid_chars):
            raise ValueError(f"파일 이름에 허용되지 않는 문자가 포함되어 있습니다: {', '.join(invalid_chars)}")

        #pdf 확장자 체크
        if not v.lower().endswith('.pdf'):
            raise ValueError("파일 이름은 반드시 .pdf 확장자로 끝나야 합니다.")
        # 3. Windows 예약어 검사 (확장자 제외)
        reserved_names = {
            "CON", "PRN", "AUX", "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }
        name_part = v.split('.')[0].upper()
        if name_part in reserved_names:
            raise ValueError(f"파일 이름에 허용되지 않는 예약어가 포함되어 있습니다: {name_part}")

        # 4. ASCII 제어문자(0-31, 127) 검사
        if any(ord(c) < 32 or ord(c) == 127 for c in v):
            raise ValueError("파일 이름에 ASCII 제어문자(0-31, 127)는 포함될 수 없습니다.")

        # 5. AWS S3에서 특별한 처리가 필요한 문자 검사
        # 앰퍼샌드(&), 달러($), At(@), 같음(=), 세미콜론(;), 슬래시(/),
        # 콜론(:), 더하기(+), 공백, 쉼표(,), 물음표(?)는 URL 인코딩 필요 - 여기서는 경고를 던짐
        special_chars = set("&$@=;/:+ ,?")
        if any(char in special_chars for char in v):
            raise ValueError(
                f"파일 이름에 S3 업로드 시 URL 인코딩이 필요한 문자가 포함되어 있습니다: {' '.join(special_chars)}"
            )
        return v 

    @field_validator('mime_type')
    def validate_mime_type(cls,v):
        """
        MIME 타입 유효성 검증
        - PDF 파일만 허용
        """
        allowed_mime_types = ['application/pdf']
        if v.lower() not in allowed_mime_types:
            raise ValueError(f"허용되지 않는 MIME 타입입니다. 허용된 타입: {', '.join(allowed_mime_types)}")
        return v.lower()

    @field_validator('file_size')
    def validate_file_size(cls,v):
        """
        파일 크기 유효성 검증
        AWS Lambda의 페이로드 제한과 사용자 경험을 고려
        """
        # 최대 500MB 제한
        max_size = other_settings.max_Size
        if v > max_size:
            max_size_mb = max_size / (1024 * 1024)
            raise ValueError(f"파일 크기는 {max_size_mb}MB를 초과할 수 없습니다.")
        if v <= 0:
            raise ValueError("파일 크기는 0보다 커야 합니다.")

        
        return v

    @field_validator('user_id')
    def validate_user_id(cls, v):
        """
        사용자 ID 유효성 검증
        - 양수 정수만 허용
        """
        if not isinstance(v, int) or v <= 0:
            raise ValueError("사용자 ID는 양수 정수여야 합니다.")
        return v

    class Config:
        """
        Pydantic 모델 설정
        FastAPI 자동 문서화와 JSON 스키마 생성을 위한 설정
        """
        schema_extra = {
            "example": {
                "user_id": 123,
                "file_name": "example.pdf",
                "mime_type": "application/pdf",
                "file_size": 204800,
                "description": "Sample PDF file for upload"
            }
        }
        allow_population_by_field_name = True


class FileUploadResponse(BaseModel):
    """
    파일 업로드 응답 모델
    File 테이블 구조를 반영한 응답 스키마
    """

    #File 테이블 기반 구조를 반영한 응답 스키마
    id: int = Field(..., description="파일 ID")
    user_id: int = Field(..., description="사용자 ID")
    file_name: str = Field(..., description="업로드된 파일 이름")
    file_path: str = Field(..., description="S3에 저장된 파일 경로")
    mime_type: str = Field(..., description="파일 MIME 타입")
    file_size: int = Field(..., description="파일 크기 (바이트 단위)")
    created_at: datetime = Field(..., description="파일 업로드 시간")
    updated_at: datetime = Field(..., description="파일 정보 수정 시간")

    # 추가적인 메타데이터 필드
    success: bool = Field(..., description="업로드 성공 여부")
    message: Optional[str] = Field(None, description="추가 메시지")
    presigned_url: Optional[str] = Field(None, description="S3에서 파일에 접근할 수 있는 사전 서명된 URL")  
    
    class Config:
        orm_mode = True

        schema_extra = {
            "example": {
                "id": 1,
                "user_id": 123,
                "file_name": "example.pdf",
                "file_path": "uploads/example.pdf",
                "mime_type": "application/pdf",
                "file_size": 204800,
                "created_at": "2023-10-01T12:00:00Z",
                "updated_at": "2023-10-01T12:00:00Z",
                "success": True,
                "message": "File uploaded successfully",
                "presigned_url": "https://s3.amazonaws.com/bucket/uploads/example.pdf"
            }
        }

class FileListResponse(BaseModel):
    """
    파일 목록 조회 응답을 위한 Pydantic 모델
    """
    id : int
    file_name: str
    file_size: int
    mime_type: str
    created_at: datetime

    class Config:
        orm_mode = True
        

class FileUploadError(BaseModel):
    """
    파일 업로드 실패 응답을 위한 Pydantic 모델
    """
    success: bool = Field(False, description="업로드 실패 표시")
    error_code: str = Field(..., description="에러 코드")
    error_message: str = Field(..., description="에러 메시지")
    details: Optional[dict] = Field(None, description="상세 에러 정보")

    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error_code": "FILE_SIZE_EXCEEDED",
                "error_message": "파일 크기가 50MB를 초과했습니다",
                "details": {
                    "max_size": "50MB",
                    "uploaded_size": "75MB"
                }
            }
        }






