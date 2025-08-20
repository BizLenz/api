"""
CognitoIdpWrapper: boto3 cognito-idp 클라이언트를 감싸는 래퍼 클래스.

주요 목적
- 복잡한 Cognito 파라미터(SecretHash/SECRET_HASH, AuthFlow 등)와 포맷을 한 곳에서 표준화하여
  라우터/서비스 코드의 복잡도를 낮춥니다[1][4][10].
- 클라이언트 시크릿이 있는 App Client의 경우, SecretHash를 HMAC-SHA256(username+client_id)을
  client_secret 키로 계산 후 Base64 인코딩하여 API에 포함합니다(예: sign_up의 SecretHash,
  initiate_auth의 AuthParameters.SECRET_HASH)[1][10][11].
- sign_up, confirm_sign_up, initiate_auth(USER_PASSWORD_AUTH) 등 공식 문서의 필수/선택 파라미터
  규칙을 내부에서 일관되게 적용합니다[4][10][14].

핵심 기능
- sign_up: ClientId/Username/Password(+ UserAttributes: email, phone_number 등) 전달,
  App Client에 client_secret이 있으면 SecretHash 포함[1][14].
- confirm_sign_up: ClientId/Username/ConfirmationCode(+ SecretHash 옵션) 호출[11].
- initiate_auth(USER_PASSWORD_AUTH): AuthFlow="USER_PASSWORD_AUTH"로 호출하고
  AuthParameters에 USERNAME, PASSWORD(필수), client_secret이 있으면 SECRET_HASH 추가[4][10][7].

"""




from __future__ import annotations

import base64
import hashlib
import hmac
import re
from typing import Dict, List, Optional

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

E164_RE = re.compile(r"^\+[1-9]\d{1,14}$")

def to_e164(phone: str, default_country_code: str = "+82") -> str:
    """
    간단한 E.164 보정 함수.(전화번호 보정)
    - 입력이 이미 +로 시작하면 그대로 검사
    - 0으로 시작하는 국내 번호는 국가코드를 접두
    실제 서비스에서는 libphonenumber 같은 검증 라이브러리 사용을 권장합니다.
    """
    p = phone.strip()
    if p.startswith("+"):
        if not E164_RE.match(p):
            raise ValueError(f"Invalid E.164 format: {p}")
        return p

    # 0으로 시작하는 번호는 접두 0을 제거, 국가코드를 붙여서 E.164 형식으로 변환
    p= p.lstrip("0")
    candidate = f"{default_country_code}{p}"
    if not E164_RE.match(candidate):
        raise ValueError(f"Invalid E.164 format: {candidate}")
    return candidate



class CognitoIdpWrapper:
    """
    AWS Cognito User Pool용 래퍼 클래스.
    - sign_up: 사용자 회원가입 (이메일 등 속성 포함)
    - confirm_sign_up: 가입 확인 코드 검증
    - initiate_auth: USER_PASSWORD_AUTH 플로우로 로그인 토큰 발급

    주의:
    - App Client에 Client secret이 있으면 SecretHash를 반드시 포함해야 합니다.
      공식 문서의 파라미터 정의를 그대로 따릅니다.
    """
    def __init__(
        self, 
        region_name: str,
        user_pool_id: str,
        client_id: str,
        client_secret: Optional[str] = None,
        boto3_client: Optional[BaseClient] = None,
    ) -> None:
        """
        region_name: AWS 리전 (예: ap-northeast-2)
        user_pool_id: Cognito User Pool ID
        client_id: User Pool의 App Client ID
        client_secret: (선택) App Client Secret
        boto3_client: (선택) 테스트 등을 위한 주입용 클라이언트
        """
        self.region_name = region_name
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.client_secret = client_secret  

        # boto3 클라이언트가 주입되지 않으면 새로 생성
        self.client: BaseClient = boto3_client or boto3.client(
            "cognito-idp",
            region_name=self.region_name,
        )
    

    def _calc_secret_hash(self, username: str) -> str:
        """
        Cogntio App Client에 Client secret이 설정된 경우, API 요청에 포함해야 하는 SecretHash를 계산하는 함수
        핵심 목적:
        클라이언트가 진짜 client secret을 알고 있는지를 서버 측에서 검증할 수 있도록 하는 서명값(SecretHash)을 생성함.
        """
        if not self.client_secret:
            raise ValueError("Client secret is not configured but required.")
        key = self.client_secret.encode("utf-8")
        msg = (username + self.client_id).encode("utf-8")
        digest = hmac.new(key, msg, hashlib.sha256).digest()

        return base64.b64encode(digest).decode()
        
    

    def forgot_password(self, username: str, secret_hash_username: Optional[str] = None)-> Dict:
        """
        비밀번호 재설정 코드 발송(ForgotPassword).
        - 필수: ClientId, Username
        - 옵션: SecretHash(클라이언트 시크릿 사용 시)
        - 응답: CodeDeliveryDetails(발송 채널/대상) 포함
        """
        kwargs: Dict = {
            "ClientId": self.client_id,
            "Username": username,
        }
        if self.client_secret:
            base_username = secret_hash_username or username
            kwargs["SecretHash"] = self._calc_secret_hash(base_username)
        try:
            return self.client.forgot_password(**kwargs) # 공식 메서드
        except ClientError as e:
            raise e


    def confirm_forgot_password(
        self,
        username: str,
        confirmation_code: str,
        new_password: str,
        secret_hash_username: Optional[str] = None,
    ) -> Dict:
        """
        비밀번호 재설정 완료(ConfirmForgotPassword).
        - 필수: ClientId, Username, ConfirmationCode, Password(새 비밀번호)
        - 옵션: SecretHash(클라이언트 시크릿 사용 시)
        - 응답: 빈 dict {} 성공 시
        """
        kwargs: Dict = {
            "ClientId": self.client_id,
            "Username": username,
            "ConfirmationCode": confirmation_code,
            "Password": new_password,
        }
        if self.client_secret:
            base_username = secret_hash_username or username
            kwargs["SecretHash"] = self._calc_secret_hash(base_username)
        try:
            return self.client.confirm_forgot_password(**kwargs)  # 공식 메서드
        except ClientError as e:
            raise e
        