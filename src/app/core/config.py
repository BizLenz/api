
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional, Literal

class Settings(BaseSettings):
   """환경 변수 기반 설정 클래스
   로컬 개발, 스테이징, 프로덕션 환경을 구분하여 관리
   """
    
   #프로젝트 기본 정보
   project_name: str = "BizLenz"
   version: str = "1.0.0"
   environment: str = Field(default="development", env="ENVIRONMENT")
   debug: bool = Field(default=True, env="DEBUG")

   # 데이터베이스 설정 (RDS)
   db_user: str = Field(env="DB_USER")
   db_password: str = Field(env="DB_PASSWORD") 
   db_host: str = Field(env="DB_HOST")
   db_port: int = Field(default=5432, env="DB_PORT")
   db_name: str = Field(env="DB_NAME")

   #AWS 기본 설정
   aws_access_key_id: str | None = Field(None, env="AWS_ACCESS_KEY_ID")
   aws_secret_access_key: str | None = Field(None, env="AWS_SECRET_ACCESS_KEY")
   aws_region: str | None = Field(None, env="AWS_REGION")
   aws_account_id: str | None = Field(None, env="AWS_ACCOUNT_ID")

   #AWS API Gateway 설정
   api_gateway_url: Optional[str] = Field(debug=True, env="API_GATEWAY_URL")
   api_gateway_stage: str = Field(default="dev", env="API_GATEWAY_STAGE") # dev, staging, prod
   api_gateway_api_key: Optional[str] = Field(default=None, env="API_GATEWAY_API_KEY")

   #API Gateway 요청 제한 설정
   api_gateway_throttle_burst_limit: int = Field(default=1000, env="API_THROTTLE_BURST")  # 버스트 제한
   api_gateway_throttle_rate_limit: int = Field(default=500, env="API_THROTTLE_RATE")  # 초당 요청 수 제한

   # API Gateway CORS 설정
   api_cors_allow_credentials: bool = Field(default=True, env="API_CORS_ALLOW_CREDENTIALS")
   api_cors_max_age: int = Field(default=86400, env="API_CORS_MAX_AGE")  # 24시간

   # CORS 설정
   origins = [
   "http://localhost:3000",  # 로컬 개발 환경 허용
   "https://mybizlenz.com",  # 실제 서비스 도메인
   ]

   # AWS S3 설정
   s3_bucket_name: str = Field(default="bizlenz-files", env="S3_BUCKET_NAME")
   s3_upload_folder: str = Field(default="uploads", env="S3_UPLOAD_FOLDER")
   s3_processed_folder: str = Field(default="processed", env="S3_PROCESSED_FOLDER")
   s3_temp_folder: str = Field(default="temp", env="S3_TEMP_FOLDER")
   s3_max_file_size: int = Field(default=50 * 1024 * 1024, env="S3_MAX_FILE_SIZE")  # 50MB

   # S3 Pre-signed URL 설정
   presigned_url_expiration: int = Field(3600, env="PRESIGNED_URL_EXPIRATION")  # 1시간
   presigned_url_method: Literal["GET", "PUT", "POST"] = Field("GET", env="PRESIGNED_URL_METHOD")

   class Config:
   # 루트 디렉토리에 있는 .env 파일을 읽어 환경변수로 반영
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()