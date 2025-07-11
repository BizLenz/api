from fastapi import FastAPI, Request, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
import httpx
import json

auth_api = FastAPI()

COGNITO_REGION = "ap-northeast-2"
COGNITO_USER_POOL_ID = "ap-northeast-2_abc123"  # 우리들만의 Cognito 설정으로 바꿔야 함
COGNITO_JWKS_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
COGNITO_ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
COGNITO_AUDIENCE = "client_id_from_cognito"  # JWT 토큰이 나를 위해 발급 된 것인지 확인하는 용도



#jwks를 가져오는 변수 및 함수
jwks = {}

class TokenRequest(BaseModel):
    credentials:str

async def get_public_keys(): # JWKS를 가져오면서, 서명이 진짜인지 확인하기 위한 공개 키를 가져오는 함수
    global jwks
    if not jwks:
        async with httpx.AsyncClient() as client:
            resp = await client.get(COGNITO_JWKS_URL)
            jwks = resp.json()
    return jwks


#JWT 인증 토큰 검증 함수 , 클라이언트가 보낸 http 요청에서 access token만을 추출
async def verify_cognito_token(
    token: str = Depends(lambda request: request.headers.get("Authorization").split()[1])
):
# 공개키 인증 이후 토큰을 검증
keys = await get_public_keys()

    for key in keys["keys"]:
        try:
            public_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
            decoded_token = jwt.decode( # JWT 토큰을 디코딩하고 검증
                token,
                public_key,
                algorithms=["RS256"],
                audience=COGNITO_AUDIENCE,
                issuer=COGNITO_ISSUER
            )
            return decoded_token # 유효한 토큰을 반환
        except JWTError:
            continue     
    raise HTTPException(status_code=401, detail="Invalid Cognito token") #유효하지 않은 토큰 발생

# JWT 토큰을 검증하는 API 엔드포인트
@auth_api.post("/login")
async def login_with_JWTtoken(token_request: TokenRequest):
    token = token_request.credentials
    user_infor=await decoded_token(token)

    return{
        "status": "success"
        "message":"Login successfully",
        "acceess_token": token
    }


import boto3
from botocore.exceptions import ClientError

AWS_REGION = "ap-northeast-2"
COGNITO_USER_POOL_ID = "ap-northeast-2_abc123"  # 우리들만의 Cognito 설정으로 바꿔야 함
CLIENT_ID = "client_id_from_cognito"  # Cognito 클라이언트 ID

class SignupRequest(BaseModel):
    email: str #user_info 파라미터
    password: str

cognito_client = boto3.client('cognito-idp', region_name=AWS_REGION)

# 회원가입 API 엔드포인트
@auth_api.post("/signup") 
def signup_user(user:SignupRequest):
    try:
        response = cognito_client.sign_up( # Cognito에 회원가입 요청(sign_up은 boto3 라이브러리에서 제공하는 함수)
            ClientId=CLIENT_ID,
            Username=user.email,
            Password=user.password,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': user.email
                }
            ]
        )
        return {"status":"success","message": "User registered successfully", "user_sub": response['UserSub']}

    except ClientError as e: # Cognito에서 발생하는 예외 처리
        raise HTTPException(
            status_code=400,
            detail=str(e.response['Error']['Message'])
        )


class ForgottenPasswordRequest(BaseModel):
    email_info: EmailStr
    confirmation_code: str
    new_password: str

@auth_api.post("/forgot-password") # 비밀번호 재설정 요청 엔드포인트
def forgot_password(req:ForgottenPasswordRequest):
    try:
        #AWS Cognito에 비밀번호 재설정 요청(코드 전송)
        response = cognito_client.forgot_password(
            ClientId=CLIENT_ID,
            Username=req.email_info
        )
        return {"status": "success","message": "Verification email sent"}
    except ClientError as e:
        raise HTTPException(status_code=400, detail=e.response["Error"]["Message"])


@auth_api.post("/reset-password") # 비밀번호 재설정 엔드포인트
def confirm_forgot_password(req: ForgottenPasswordRequest):
    try:
        #AWS Cognito에 비밀번호 재설정 요청(코드 확인 및 새 비밀번호 설정)
        response = cognito_client.confirm_forgot_password(
            ClientId=CLIENT_ID,
            Username=req.email_info,
            ConfirmationCode=req.confirmation_code,
            Password=req.new_password
        )
        return {"status": "success", "message": "Reset Password Successfully"}
    except ClientError as e:
        raise HTTPException(status_code=400, detail=e.response["Error"]["Message"])