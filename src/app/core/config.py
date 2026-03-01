from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    environment: str = "dev"
    debug: bool = True

    # Database Settings
    db_user: str = "postgres"
    db_password: str = ""
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "postgres"

    # S3-Compatible Storage
    # Leave storage_endpoint_url as None to use AWS S3 directly.
    # Set to e.g. "http://localhost:9000" for MinIO or "https://..." for Cloudflare R2.
    storage_endpoint_url: str | None = None
    storage_bucket_name: str = "bizlenz-files"
    storage_region: str | None = None

    # Credentials used for S3-compatible storage (key ID / secret)
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # Storage folder layout
    s3_upload_folder: str = "uploads"
    s3_processed_folder: str = "processed"
    s3_temp_folder: str = "temp"
    s3_max_file_size: int = 50 * 1024 * 1024  # 50 MB

    # Pre-signed URL settings
    presigned_url_expiration: int = 3600  # 1 h
    presigned_url_method: Literal["GET", "PUT", "POST"] = "GET"

    # Generic OIDC Authentication
    # Set AUTH_JWKS_URL to e.g. "https://your-auth-server/api/auth/jwks" (better-auth default).
    auth_jwks_url: str | None = None
    auth_issuer: str | None = None
    auth_audience: str | None = None

    # CORS
    api_cors_allow_credentials: bool = True
    api_cors_max_age: int = 86400  # 24 h
    # Set CORS_ALLOWED_ORIGINS to a JSON array, e.g. '["https://app.example.com"]'
    cors_allowed_origins: list[str] = Field(default=["http://localhost:3000"])

    # Google Gemini
    google_api_key: str | None = None
    gemini_model_analysis: str = "gemini-2.5-flash"


# Global settings instance
settings = Settings()
