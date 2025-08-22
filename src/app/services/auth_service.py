from __future__ import annotations
from fastapi import HTTPException, status
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session
from app.crud import user as user_crud
from app.models.models import User
from app.core.config import settings
from app.clients.cognito_wrapper import CognitoIdpWrapper
from app.schemas.user import ForgotPasswordResponse


cognito_wrapper = CognitoIdpWrapper(
    region_name=settings.cognito_region,
    user_pool_id=settings.cognito_user_pool_id,
    client_id=settings.cognito_client_id,
    client_secret=settings.cognito_client_secret,
)


def ensure_profile(db:Session, cognito_sub: str) -> User:
    """사용자 프로필이 존재하는지 확인하고, 없으면 생성합니다."""
    return user_crud.create_if_not_exists(db,cognito_sub)

def get_profile(db:Session, cognito_sub: str) -> User:
    """사용자 프로필을 조회하고, 없으면 404 에러를 발생시킵니다."""
    user = user_crud.get_by_sub(db,cognito_sub)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

def add_token_usage(db:Session, cognito_sub: str, inc: int):
    """사용자 토큰 사용량을 증가시킵니다."""
    if inc<=0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token usage increment")
    user = user_crud.increment_token_usage(db,cognito_sub,inc)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

