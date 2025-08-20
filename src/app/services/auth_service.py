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

def request_password_reset(username: str) -> ForgotPasswordResponse:
    """
    비밀번호 재설정 코드 발송을 처리하는 서비스 함수입니다.
    Cognito의 ForgotPassword API를 호출하는 비즈니스 로직을 담당합니다.

    Args:
        username (str): 재설정을 요청한 사용자의 이름(이메일 등).

    Returns:
        ForgotPasswordResponse: 코드 전달 정보를 담은 응답 객체입니다.
    """
    try:
        response = cognito_wrapper.forgot_password(username=username)
        delivery_details = response.get("CodeDeliveryDetails",{})

        return ForgotPasswordResponse(
            destination = delivery_details.get("Destination"),
            delivery_medium = delivery_details.get("DeliveryMedium"),
            attribute_name = delivery_details.get("AttributeName"),
        )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "UserNotFoundException":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        elif error_code == "LimitExceededException":
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

def confirm_password_reset(username:str, confirmation_code:str, new_password:str) -> None:
    """
    비밀번호 재설정을 완료하는 서비스 함수
    """
    try:
        cognito_wrapper.confirm_forgot_password(
            username=username,
            confirmation_code=confirmation_code,
            new_password=new_password,
        )

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "CodeMismatchException":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid confirmation code")
        elif error_code == "ExpiredCodeException":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Confirmation code has expired")
        elif error_code == "UserNotFoundException":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

