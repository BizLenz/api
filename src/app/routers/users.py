# src/app/routers/users.py

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from src.app.core.config import settings
from jose import JWTError, jwt
import httpx
import boto3
from botocore.exceptions import ClientError

router = APIRouter()

# Cognito 기본 설정
COGNITO_REGION = settings.COGNITO_REGION
USER_POOL_ID = settings.COGNITO_USER_POOL_ID
CLIENT_ID = settings.COGNITO_CLIENT_ID
JWKS_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{USER_POOL_ID}"

# boto3 클라이언트
cognito_client = boto3.client("cognito-idp", region_name=COGNITO_REGION)

# 메모리 캐시된 JWKS
jwks = {}


# 요청 스키마
class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class TokenRequest(BaseModel):
    credentials: str


class ForgottenPasswordRequest(BaseModel):
    email_info: EmailStr
    confirmation_code: str
    new_password: str


# JWKS 키 가져오기
async def get_public_keys():
    global jwks
    if not jwks:
        async with httpx.AsyncClient() as client:
            resp = await client.get(JWKS_URL)
            jwks = resp.json()
    return jwks


# JWT 토큰 검증용 의존성
async def verify_cognito_token(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    token = auth_header.split()[1]
    keys = await get_public_keys()

    for key in keys["keys"]:
        try:
            public_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
            decoded_token = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=CLIENT_ID,
                issuer=ISSUER,
            )
            return decoded_token
        except JWTError:
            continue

    raise HTTPException(status_code=401, detail="Invalid Cognito token")


# 회원가입
@router.post("/signup")
def signup_user(user: SignupRequest):
    try:
        response = cognito_client.sign_up(
            ClientId=CLIENT_ID,
            Username=user.email,
            Password=user.password,
            UserAttributes=[{"Name": "email", "Value": user.email}],
        )
        return {
            "status": "success",
            "message": "User registered successfully",
            "user_sub": response["UserSub"],
        }
    except ClientError as e:
        raise HTTPException(status_code=400, detail=e.response["Error"]["Message"])


# 로그인 (JWT 토큰 유효성 확인)
@router.post("/login")
async def login_with_JWTtoken(token_request: TokenRequest):
    token = token_request.credentials
    decoded = await verify_cognito_token(
        Request(
            scope={
                "type": "http",
                "headers": [(b"authorization", f"Bearer {token}".encode())],
            }
        )
    )
    return {
        "status": "success",
        "message": "Login successful",
        "access_token": token,
        "claims": decoded,
    }


# 비밀번호 재설정 요청
@router.post("/forgot-password")
def forgot_password(req: ForgottenPasswordRequest):
    try:
        cognito_client.forgot_password(ClientId=CLIENT_ID, Username=req.email_info)
        return {"status": "success", "message": "Verification code sent to email"}
    except ClientError as e:
        raise HTTPException(status_code=400, detail=e.response["Error"]["Message"])


# 비밀번호 재설정 완료
@router.post("/reset-password")
def reset_password(req: ForgottenPasswordRequest):
    try:
        cognito_client.confirm_forgot_password(
            ClientId=CLIENT_ID,
            Username=req.email_info,
            ConfirmationCode=req.confirmation_code,
            Password=req.new_password,
        )
        return {"status": "success", "message": "Password reset successful"}
    except ClientError as e:
        raise HTTPException(status_code=400, detail=e.response["Error"]["Message"])
