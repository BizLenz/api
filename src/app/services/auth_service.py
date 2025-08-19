"""
AuthService: Cognito 래퍼(CognitoIdpWrapper)를 주입받아 인증 업무 로직을 담당하는 서비스 계층.

역할
- RDS 스키마(users 테이블) 기반 입력값을 Cognito 표준/커스텀 속성으로 매핑하여 호출합니다.
  - email → Cognito 표준 속성 email[4][8]
  - phone_number → Cognito 표준 속성 phone_number(E.164 형식 필수: +국가코드부터 시작, 숫자만)[4]
  - address → Cognito 커스텀 속성 custom:address(사전 정의 필요)
- 비즈니스 흐름을 캡슐화하고, 라우터(FastAPI)에서는 단순히 서비스만 호출하도록 하여 코드 복잡도를 낮춥니다.

핵심 기능
- sign_up: Cognito SignUp 호출을 위해 username/password 및 UserAttributes(email, phone_number, custom:address)를 구성해 전달합니다[8][4].
- confirm_sign_up: 사용자에게 발송된 확인 코드를 받아 ConfirmSignUp 호출을 수행합니다(SecretHash는 클라이언트 시크릿 사용 시 필요)[18][13].
- sign_in: InitiateAuth(AuthFlow=USER_PASSWORD_AUTH)로 로그인 시도하며, USERNAME/PASSWORD(필수)와 필요 시 SECRET_HASH를 포함해 토큰을 수신합니다[9][6].

에러 처리
- boto3 ClientError를 상위 레이어(라우터)에서 HTTPException으로 변환할 수 있도록 예외를 그대로 전달합니다.

비고
- Client secret이 설정된 App Client라면 SecretHash/SECRET_HASH 계산이 필요하며, 이 로직은 Cognito 래퍼 내부에서 처리됩니다[9][6].
- USER_PASSWORD_AUTH 플로우는 User Pool의 클라이언트 설정에서 활성화되어 있어야 합니다[9][19].
"""

from __future__ import annotations
from fastapi import Depends
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session
from app.database import get_db
from app.clients.cognito_wrapper import CognitoIdpWrapper
from app.schemas.auth_schemas import(
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ConfirmForgotPasswordRequest,
    SignUpRequest, SignUpResponse,SignInRequest,SignInResponse,
)
from app.core.config import settings

class AuthService:
    def __init__(self, db:Session, cognito: CognitoIdpWrapper):
        self.db = db 
        self.cognito = cognito
    
    def sign_up(self, req:SignUpRequest) -> SignUpResponse:
        """
        RDS users 스키마 필드 → Cognito 속성 매핑:
        - username: Cognito Username (필수)
        - password: Cognito Password (필수, 원문 전달)
        - email: email (표준 속성)
        - phone_number: phone_number (표준 속성, E.164)
        - address: custom:address (커스텀)
        주의: password_hash는 RDS 보관용이며, Cognito에는 원문 비밀번호가 필요합니다.
        """
        try:
            resp = self.cognito.sign_up(
                username=str(req.username),
                password=req.password,
                email=str(req.email) if req.email else None,
                phone_number=str(req.phone_number) if req.phone_number else None,
                address=str(req.address) if req.address else None,
            )
            code_details = resp.get("CodeDeliveryDetails", {})
            return SignUpResponse(
                user_confirmed=resp.get("UserConfirmed", False),
                user_sub=resp["UserSub"],
                code_delivery_destination=code_details.get("Destination"),
                delivery_medium=code_details.get("DeliveryMedium"),
                attribute_name=code_details.get("AttributeName"),
            )
        except ClientError as e:
            raise e
    def sign_in(self, req: SignInRequest)->SignInResponse:
        """
        사용자 이름과 비밀번호로 로그인 인증을 시작하고 토큰 정보를 반환합니다.
        - 챌린지(Challenge)가 필요한 경우, 토큰 대신 챌린지 관련 정보를 반환합니다.
        """
        try:
            resp=self.cognito.initiate_auth(
                username = req.username,
                password = req.password
            )
            if "AuthenticationResult" in resp:
                auth_result = resp["AuthenticationResult"]
                return SignInResponse(
                    access_token=auth_result.get("AccessToken"),
                    id_token=auth_result.get("IdToken"),
                    refresh_token=auth_result.get("RefreshToken"),
                    expires_in=auth_result.get("ExpiresIn"),
                    token_type=auth_result.get("TokenType"),
                    challenge_name=None,
                    session=None,
                    challenge_parameters=None
                )   
            # 챌린지가 필요한 경우, 챌린지 정보를 반환합니다.
            elif "ChallengeName" in resp:
                return SignInResponse(
                    access_token=None,
                    id_token=None,
                    refresh_token=None,
                    expires_in=None,
                    token_type=None,
                    challenge_name=resp.get("ChallengeName"),
                    session=resp.get("Session"),
                    challenge_parameters=resp.get("ChallengeParameters")
                ) 
            # 예상치 못한 응답인 경우
            else:
                raise Exception("Unexpected response from Cognito service")    
        except ClientError as e:
            raise e

    def forgot_password(self, req: ForgotPasswordRequest) -> ForgotPasswordResponse:
        """
        비밀번호 재설정 코드 발송
        """
        try:
            resp = self.cognito.forgot_pasword(username=req.username)
            details = resp.get("CodeDeliveryDetails", {})
            return ForgotPasswordResponse(
                destination=details.get("Destination"),
                delivery_medium=details.get("DeliveryMedium"),
                attritubute_name=details.get("AttributeName"),
            )
        except ClientError as e:
            raise e
            
    def confirm_forgot_password(self, req: ConfirmForgotPasswordRequest) -> dict:
        """
        코드 확인 및 새 비밀번호 설정
        성공 시 빈 dict 반환
        """
        try:
            self.cognito.confirm_forgot_password(
                username=req.username,
                confirmation_code=req.confirmation_code,
                password=req.password,
            )
            return {"status": "CONFIRMED"}

        except ClientError as e:
            raise e
        
def get_cognito_client() -> CognitoIdpWrapper:
    """
    CognitoIdpWrapper 인스턴스를 생성하고 반환합니다.
    """
    return CognitoIdpWrapper(
        region_name=settings.aws_region,
        user_pool_id=settings.cognito_user_pool_id,
        client_id=settings.cognito_client_id,
        client_secret=settings.cognito_client_secret
    )

def get_auth_service(
    db: Session = Depends(get_db),
    cognito_client: CognitoIdpWrapper = Depends(get_cognito_client)
) -> AuthService:
    """
    AuthService 클래스의 인스턴스를 생성하고 반환합니다.
    데이터베이스 세션과 Cognito 클라이언트 인스턴스를 주입합니다.
    """
    return AuthService(
        db=db,
        cognito=cognito_client
    )



