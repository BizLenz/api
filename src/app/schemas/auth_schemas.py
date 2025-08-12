from pydantic import BaseModel, Emailstr, Field
from typing import Optional

class SignUpRequest(BaseModel):
    username: str = Field(..., description ="사용자 이름, 이메일/전화번호 형식도 가능")
    password: str =Field(..., description="비밀번호, 최소 8자 이상, Cognito에 전달할 원문 비밀번호")
    email: Optional[Emailstr] = Field(None, description = "이메일 주소")
    phone_number: Optional[str] = Field(None, description="RDS users.phone_number → Cognito phone_number(E.164:+821012345678)")
    address: Optional[str] = Field(None, description = "주소 -> Cognito custom:address")
    
class SignUpResponse(BaseModel):
    user_confirmed: bool
    user_sub: str
    code_delivery_destination: Optional[str] = None
    delivery_medium: Optional[str] = None
    attribute_name: Optional[str] = None

class ConfirmSignUpRequest(BaseModel):
    # 확인 코드는 이메일/휴대폰 등으로 전달되므로 username 타입 제한을 두지 않습니다.
    username: str = Field(..., description="가입 시 사용한 username (이메일/전화번호/문자열)")
    confirmation_code: str = Field(..., description="가입 확인 코드")

class ConfirmSignUpResponse(BaseModel):
    status: str = Field(..., description='예: "CONFIRMED"')

class SignInRequest(BaseModel):
    username: str = Field(..., description="사용자 이름, 이메일/전화번호 형식도 가능")
    password: str = Field(..., description="비밀번호, Cognito에 전달할 원문 비밀번호")

class SignInResponse(BaseModel):
    access_token: Optional[str] = None
    id_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    token_type: Optional[str] = None

    """
    챌린지는 사용자가 토큰을 받기 전에 추가로 통과해야 하는 인증 단계로, 예를 들어 MFA 코드 입력(SMS/Email/Authenticator), 
    비밀번호 변경 요구(NEW_PASSWORD_REQUIRED), 또는 커스텀 질문/OTP 같은 추가 검증을 의미한다.
    앱이 InitiateAuth를 호출했을 때 Cognito가 추가 단계가 필요하다고 판단하면 응답에  ChallengeName, ChallengeParameters, Session을 담아 보내며, 
    클라이언트는 이 정보로 다음 단계 입력을 받아 RespondToAuthChallenge로 답한다
    """
    
    # 챌린지 대응을 위한 필드
    challenge_name: Optional[str] = None
    session: Optional[str] = None
    challenge_parameters: Optional[Dict[str, Any]] = None