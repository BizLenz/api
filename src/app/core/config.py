# src/app/core/config.py
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    """환경 변수 기반 설정 클래스
    로컬 개발, 스테이징, 프로덕션 환경을 구분하여 관리
    """
    
    # 프로젝트 기본 정보
    project_name: str = "BizLenz"
    version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # 수정: 데이터베이스 설정 (Alembic 오류 해결용 기본값 추가)
    db_user: str = Field(default="postgres", env="DB_USER")
    db_password: str = Field(default="", env="DB_PASSWORD") 
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="postgres", env="DB_NAME")
    
    # 수정: AWS 기본 설정 (PR 리뷰 반영 - Optional[str] 유지하되 Field 수정)
    aws_access_key_id: str | None = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: str | None = Field(default="ap-northeast-2", env="AWS_REGION")
    aws_account_id: str | None = Field(default=None, env="AWS_ACCOUNT_ID")
    
    # AWS API Gateway 설정
    api_gateway_url: str | None = Field(default=None, env="API_GATEWAY_URL")
    api_gateway_stage: str = Field(default="dev", env="API_GATEWAY_STAGE")  # dev, staging, prod
    api_gateway_api_key: str | None = Field(default=None, env="API_GATEWAY_API_KEY")
    
    # API Gateway 요청 제한 설정
    api_gateway_throttle_burst_limit: int = Field(default=1000, env="API_THROTTLE_BURST")  # 버스트 제한
    api_gateway_throttle_rate_limit: int = Field(default=500, env="API_THROTTLE_RATE")  # 초당 요청 수 제한
    
    # API Gateway CORS 설정
    api_cors_allow_credentials: bool = Field(default=True, env="API_CORS_ALLOW_CREDENTIALS")
    api_cors_max_age: int = Field(default=86400, env="API_CORS_MAX_AGE")  # 24시간
    
    # AWS S3 설정
    s3_bucket_name: str = Field(default="bizlenz-files", env="S3_BUCKET_NAME")
    s3_upload_folder: str = Field(default="uploads", env="S3_UPLOAD_FOLDER")
    s3_processed_folder: str = Field(default="processed", env="S3_PROCESSED_FOLDER")
    s3_temp_folder: str = Field(default="temp", env="S3_TEMP_FOLDER")
    s3_max_file_size: int = Field(default=50 * 1024 * 1024, env="S3_MAX_FILE_SIZE")  # 50MB
    
    # S3 Pre-signed URL 설정
    presigned_url_expiration: int = Field(3600, env="PRESIGNED_URL_EXPIRATION")  # 1시간
    presigned_url_method: Literal["GET", "PUT", "POST"] = Field("GET", env="PRESIGNED_URL_METHOD")

    # Cognito 설정
    cognito_region: str = Field(default = "ap-northeast-2", env="COGNITO_REGION")
    cognito_user_pool_id: str = Field(default=None, env="COGNITO_USER_POOL_ID")
    cognito_client_id: str = Field(default=None, env="COGNITO_CLIENT_ID")
    cognito_client_secret: str | None = Field(default=None, env="COGNITO_CLIENT_SECRET")

    # 🔧 수정: Config 클래스 (Pydantic 오류 해결)
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False  # 🔧 변경: 대소문자 구분 안함
        extra = "ignore"        # 🔧 추가: 추가 필드 무시 (ValidationError 방지)

class OtherSettings(BaseSettings):
    """
    다른 설정을 위한 클래스
    필요에 따라 추가적인 설정을 여기에 정의할 수 있습니다.
    """
    max_Size: int = 50 * 1024 * 1024
    
    # 프론트엔드 오리진 목록(프로젝트 설정에 맞게 수정)
    ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://your-frontend.example.com",
    ]
    
    

# 전역 설정 인스턴스
settings = Settings()
othersettings = OtherSettings()

