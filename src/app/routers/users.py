from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from botocore.exceptions import ClientError
from app.schemas.auth_schemas import (
    SignUpRequest,
    SignUpResponse,
    ConfirmSignUpRequest,
    ConfirmSignUpResponse,
    SignInRequest,
    SignInResponse,
    ForgotPasswordRequest, 
    ForgotPasswordResponse, 
    ConfirmForgotPasswordRequest,
)

from app.services.auth_service import AuthService
from app.core.config import get_auth_service
from app.database import get_db
from app.crud.user import create_user
from sqlalchemy.orm import Session
from app.core.security import require_scope
import bcrypt

router = APIRouter(prefix="/users", tags = ["users"])


@router.get("/me")
def get_me(claims: Dict[str, Any] = Depends(require_scope("bizlenz.read"))):
    groups: List[str] = claims.get("cognito:groups", [])
    # TODO: 실제 RDS 조회 로직으로 교체 (claims["sub"] 사용)
    user = {"id": 1, "sub": claims["sub"], "email": claims.get("email"), "role": "editor", "groups": groups}
    """
    최소 데이터만 즉시 제공: 화면 상단 프로필, 메뉴 권한(읽기/쓰기 등), 온보딩 여부 판단 등 초기 렌더링에 필요한 핵심 정보를 가볍게 반환한다
    JWT Authorizer(또는 Cognito Authorizer) 통과 후, 백엔드에서 검증된 claims를 받아 sub로 DB 사용자 레코드를 조회하고, 권한 스코프(bizlenz.read 등)가 맞는지 확인한다.
    프런트는 GET /me 한 번으로 “내 프로필/역할/그룹”을 획득하고, 이후 화면 요소(업로드 버튼, 관리자 메뉴 등)를 조건부로 렌더링한다
    """
    return {"me": user}

@router.post("/signup",response_model=SignUpResponse, status_code = status.HTTP_201_CREATED)
def sign_up(req:SignUpRequest, svc: AuthService = Depends(get_auth_service), db: Session = Depends(get_db)):
    """
    회원가입 엔드포인트
    - 입력: username, password, email, phone_number, address
    - 처리: 서비스가 Cognito sign_up 호출 시 email/phone_number/address를 Cognito 속성으로 매핑, RDS users에 레코드 생성
    - 반환: 확인 코드 발송 정보와 사용자 확인 상태.
    """
    # 1) Cognito 가입
    try:
        resp = svc.sign_up(req)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "CognitoError")
        msg = e.response.get("Error", {}).get("Message", "Unknown error")
        raise HTTPException(status_code=400, detail=f"{code}: {msg}")
    # 2) RDS INSERT (비밀번호 해시 저장)
    try:
        pw_hash = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        create_user(
            db,
            username=req.username,
            password_hash=pw_hash,
            email=req.email,
            phone_number=req.phone_number,
            address=req.address,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"User creation failed: {str(e)}")
    return resp


@router.post("/confirm",response_model=ConfirmSignUpResponse)
def confirm(req: ConfirmSignUpRequest, svc:AuthService = Depends(get_auth_service)):
    """
    회원가입 확인 엔드포인트
    - 입력: username, confirmation_code
    - 처리: 서비스가 Cognito confirm_sign_up 호출
    - 반환: 확인 상태
    """
    try:
        return svc.confirm_sign_up(req)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "CognitoError")
        msg = e.response.get("Error", {}).get("Message", "Unknown error")
        raise HTTPException(status_code=400, detail=f"{code}: {msg}")

@router.post("/signin", response_model=SignInResponse)
def sign_in(req: SignInRequest, svc: AuthService = Depends(get_auth_service)):
    """
    로그인 엔드포인트
    - 입력: username, password
    - 처리: 서비스가 Cognito sign_in 호출
    - 반환: 토큰 정보 및 챌린지 대응 정보
    """
    try:
        return svc.sign_in(req)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "CognitoError")
        msg = e.response.get("Error", {}).get("Message", "Unknown error")
        raise HTTPException(status_code=400, detail=f"{code}: {msg}")

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(req: ForgotPasswordRequest, svc: AuthService = Depends(get_auth_service)):
    """
    비밀번호 재설정 코드 발송(ForgotPassword).
    - 입력: username
    - 반환: 발송 대상/채널
    """
    try:
        return svc.forgot_password(req)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "CognitoError")
        msg = e.response.get("Error", {}).get("Message", "Unknown error")
        raise HTTPException(status_code=400, detail=f"{code}: {msg}")
    
@router.post("/reset-password", status_code = status.HTTP_200_OK)
def confirm_forgot_password(req: ConfirmForgotPasswordRequest, svc: AuthService = Depends(get_auth_service)):
    """
    확인 코드 + 새 비밀번호 제출
    - 입력: username, confirmation_code, new_password
    - 반환: 상태 메시지
    """
    try:
        return svc.confirm_forgot_password(req)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "CognitoError")
        msg = e.response.get("Error", {}).get("Message", "Unknown error")
        raise HTTPException(status_code=400, detail=f"{code}: {msg}")