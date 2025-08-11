# src/app/core/config.py

from pydantic_settings import BaseSettings
from pydantic import EmailStr
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "My Business Diagnosis API"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1일

    DEFAULT_ADMIN_EMAIL: EmailStr = "admin@example.com"

    DATABASE_URL: str

    COGNITO_REGION: str
    COGNITO_USER_POOL_ID: str
    COGNITO_CLIENT_ID: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# ✅ 즉시 생성 제거
# settings = Settings()


# ✅ 지연 생성 방식으로 대체
def get_settings():
    return Settings()
