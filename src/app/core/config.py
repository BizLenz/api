from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Literal, ClassVar

class Settings(BaseSettings):
    """
    Class for environment-based configuration
    Configures on runtime based on environment variables(dev, staging, prod)
    """

    # Basic Settings
    project_name: str = "BizLenz"
    version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Database Settings
    db_user: str = Field(default="postgres", env="DB_USER")
    db_password: str = Field(default="", env="DB_PASSWORD") 
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="postgres", env="DB_NAME")

    # AWS Default Settings
    aws_access_key_id: str | None = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: str | None = Field(default="ap-northeast-2", env="AWS_REGION")
    aws_account_id: str | None = Field(default=None, env="AWS_ACCOUNT_ID")

    # AWS API Gateway
    api_gateway_url: str | None = Field(default=None, env="API_GATEWAY_URL")
    api_gateway_stage: str = Field(default="dev", env="API_GATEWAY_STAGE")  # dev, staging, prod
    api_gateway_api_key: str | None = Field(default=None, env="API_GATEWAY_API_KEY")

    # API Gateway Throttle Limits
    api_gateway_throttle_burst_limit: int = Field(default=1000, env="API_THROTTLE_BURST")
    api_gateway_throttle_rate_limit: int = Field(default=500, env="API_THROTTLE_RATE")

    # API Gateway CORS
    api_cors_allow_credentials: bool = Field(default=True, env="API_CORS_ALLOW_CREDENTIALS")
    api_cors_max_age: int = Field(default=86400, env="API_CORS_MAX_AGE")  # 24h

    # AWS S3
    s3_bucket_name: str = Field(default="bizlenz-files", env="S3_BUCKET_NAME")
    s3_upload_folder: str = Field(default="uploads", env="S3_UPLOAD_FOLDER")
    s3_processed_folder: str = Field(default="processed", env="S3_PROCESSED_FOLDER")
    s3_temp_folder: str = Field(default="temp", env="S3_TEMP_FOLDER")
    s3_max_file_size: int = Field(default=50 * 1024 * 1024, env="S3_MAX_FILE_SIZE")  # 50MB

    # S3 Pre-signed URL
    presigned_url_expiration: int = Field(3600, env="PRESIGNED_URL_EXPIRATION")  # 1h
    presigned_url_method: Literal["GET", "PUT", "POST"] = Field("GET", env="PRESIGNED_URL_METHOD")

    # Cognito
    cognito_region: str = Field(default = "ap-northeast-2", env="COGNITO_REGION")
    cognito_user_pool_id: str | None = Field(default=None, env="COGNITO_USER_POOL_ID")
    cognito_client_id: str | None = Field(default=None, env="COGNITO_CLIENT_ID")
    cognito_client_secret: str | None = Field(default=None, env="COGNITO_CLIENT_SECRET")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

class OtherSettings(BaseSettings):
    """
    Class for other settings
    """
    max_Size: ClassVar[int] = 50 * 1024 * 1024

    ALLOWED_ORIGINS: ClassVar[list[str]] = [
        "http://localhost:3000",
    ]

# Global settings instance
settings = Settings()
other_settings = OtherSettings()

