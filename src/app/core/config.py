# src/app/core/config.py

from pydantic import BaseSettings, EmailStr
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "My Business Diagnosis API"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1일

    # 이메일 인증 or 유저 관련
    DEFAULT_ADMIN_EMAIL: EmailStr = "admin@example.com"

    # DB 연결
    DATABASE_URL: str
    
    COGNITO_REGION: str
    COGNITO_USER_POOL_ID: str
    COGNITO_CLIENT_ID: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 전역으로 쓸 수 있는 settings 객체
settings = Settings()
