from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    """Environment-based configuration"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Basic Settings
    project_name: str = "BizLenz"
    version: str = "1.0.0"
    environment: str = Field(default="dev", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")

    # Database Settings
    db_user: str = Field(default="postgres", env="DB_USER")
    db_password: str = Field(default="", env="DB_PASSWORD")
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="postgres", env="DB_NAME")

    # S3-Compatible Storage
    # Leave storage_endpoint_url as None to use AWS S3 directly.
    # Set to e.g. "http://localhost:9000" for MinIO or "https://..." for Cloudflare R2.
    storage_endpoint_url: str | None = Field(default=None, env="STORAGE_ENDPOINT_URL")
    storage_bucket_name: str = Field(default="bizlenz-files", env="STORAGE_BUCKET_NAME")
    storage_region: str | None = Field(default=None, env="STORAGE_REGION")

    # Credentials used for S3-compatible storage (key ID / secret)
    aws_access_key_id: str | None = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, env="AWS_SECRET_ACCESS_KEY")

    # Storage folder layout
    s3_upload_folder: str = Field(default="uploads", env="S3_UPLOAD_FOLDER")
    s3_processed_folder: str = Field(default="processed", env="S3_PROCESSED_FOLDER")
    s3_temp_folder: str = Field(default="temp", env="S3_TEMP_FOLDER")
    s3_max_file_size: int = Field(
        default=50 * 1024 * 1024, env="S3_MAX_FILE_SIZE"
    )  # 50 MB

    # Pre-signed URL settings
    presigned_url_expiration: int = Field(3600, env="PRESIGNED_URL_EXPIRATION")  # 1 h
    presigned_url_method: Literal["GET", "PUT", "POST"] = Field(
        "GET", env="PRESIGNED_URL_METHOD"
    )

    # Generic OIDC Authentication
    # Set AUTH_JWKS_URL to e.g. "https://your-auth-server/api/auth/jwks" (better-auth default).
    auth_jwks_url: str | None = Field(default=None, env="AUTH_JWKS_URL")
    auth_issuer: str | None = Field(default=None, env="AUTH_ISSUER")
    auth_audience: str | None = Field(default=None, env="AUTH_AUDIENCE")

    # CORS
    api_cors_allow_credentials: bool = Field(
        default=True, env="API_CORS_ALLOW_CREDENTIALS"
    )
    api_cors_max_age: int = Field(default=86400, env="API_CORS_MAX_AGE")  # 24 h
    # Set CORS_ALLOWED_ORIGINS to a JSON array, e.g. '["https://app.example.com"]'
    cors_allowed_origins: list[str] = Field(
        default=["http://localhost:3000"], env="CORS_ALLOWED_ORIGINS"
    )

    # Google Gemini
    google_api_key: str | None = Field(default=None, env="GOOGLE_API_KEY")
    gemini_model_analysis: str = Field(
        default="gemini-2.5-flash", env="GEMINI_MODEL_ANALYSIS"
    )


# Global settings instance
settings = Settings()
