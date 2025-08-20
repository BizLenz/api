from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import (
    ConfirmForgotPasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    UserCreate,
    UserOut,
)
from app.services import auth_service

router = APIRouter(tags=["User Authentication & Profile"])


# 인증 관련 엔드포인트

@router.patch("/signup", response_model=UserOut)
def create_user_profile(
    payload: UserCreate,
    db: Session = Depends(get_db),
    x_cognito_sub: Optional[str] = Header(default=None, convert_underscores=False),
):
    """
    Cognito에서 회원가입/로그인을 마친 사용자의 프로필을 우리 서비스 DB(RDS)에 생성합니다.
    - 이 API는 반드시 인증된 사용자만 호출할 수 있습니다. (API Gateway Authorizer 필요)
    """
    if not x_cognito_sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing x-cognito-sub header from API Gateway mapping.",)
    user = auth_service.ensure_profile(db,x_cognito_sub)
    return UserOut.model_validate(user)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(request: ForgotPasswordRequest):
    """
    비밀번호 재설정을 위한 확인 코드 발송을 요청합니다.
    - 실제 로직은 서비스 레이어가 담당합니다.
    """
    return auth_service.request_password_reset(username=request.username)

@router.post("/confirm-forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def confirm_forgot_password(request: ConfirmForgotPasswordRequest):
    """
    확인 코드와 새 비밀번호로 비밀번호 재설정을 완료합니다.
    - 성공 시에는 본문(body) 없이 204 No Content 상태 코드를 반환합니다.
    """
    auth_service.confirm_password_reset(
        username=request.username,
        confirmation_code=request.confirmation_code,
        new_password=request.new_password,
    )
    return


# 사용자 프로필 관련 엔드포인트
@router.get("/users/me",response_model=UserOut)
def get_my_profile(
    db: Session = Depends(get_db),
    x_cognito_sub: str = Header(..., description = "Authenticated Cognito User Sub", convert_underscores=False),
):
    """
    현재 로그인된 사용자의 프로필 정보를 조회합니다.
    """
    user = auth_service.get_profile(db,x_cognito_sub)
    return UserOut.model_validate(user)

@router.post("/users/me/token-usage", response_model=UserOut)
def increase_my_token_usage(
    inc: int = Query(..., gt =0, description="증가시킬 토큰 사용량(반드시 양수)"),
    db: Session = Depends(get_db),
    x_cognito_sub: str = Header(..., description="Authenticated Cognito User Sub", convert_underscores=False),
):
    user = auth_service.add_token_usage(db,x_cognito_sub,inc)
    return UserOut.model_validate(user)