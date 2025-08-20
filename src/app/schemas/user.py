from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, Optional
from datetime import datetime


class UserBase(BaseModel):
    """
    공통 스키마 베이스
    - DB 모델로부터의 직렬화 허용(from_attributes=True)
    """
    model_config = ConfigDict(from_attributes=True)
    
class UserCreate(UserBase):
    """
    사용자 프로필 생성 입력 스키마, 기타 타입의 프로필 속성 추가시 생성
    """
    pass

class UserUpdate(UserBase):
    """
    사용자 프로필 업데이트 입력 스키마(부분 업데이트 허용)
    - 현재는 업데이트할 사용자 정의 프로필 속성이 없다면 빈 모델로 두어도 됩니다.
    - 확장 시 선택적 필드를 추가하세요.
    """
    pass

class UserOut(UserBase):
    """
    사용자 프로필 응답 스키마(기본)
    - 관계(business_plans)는 기본 응답에서 제외하여 과도한 페이로드를 방지
    - 필요 시 별도 상세 스키마(UserDetailOut)로 노출합니다.
    """
    id: int = Field(..., description = "사용자 고유 ID")
    cognito_sub: str = Field(..., description = "Cognito 사용자 고유 식별자 (JWT sub)")
    created_at: datetime = Field(..., description = "서비스 프로필 생성 일시")
    total_token_usage: int = Field(0, description="누적 토큰 사용량")

class UserDetailOut(UserOut):
    """
    상세 응답 스키마: 사용자의 연관 BusinessPlan 목록까지 함께 내려줄 때 사용
    - 목록 API에서는 과도한 응답이 될 수 있으므로 상세 조회 API에서만 선택적으로 사용하세요.
    """
    business_plans: list[BusinessPlanRef] = Field(default_factory=list)


class ForgotPasswordRequest(BaseModel):
    username: str = Field(..., description = "비밀번호 재설정 대상 username")

class ForgotPasswordResponse(BaseModel):
    destination: str | None = Field(default=None, description="코드 전달 대상(가려진 이메일/전화)")
    delivery_medium: str | None = Field(default=None, description="전달 수단(EMAIL/SMS 등)")
    attribute_name: str | None = Field(default=None, description="전달 대상 속성명(이메일/전화 등)")

class ConfirmForgotPasswordRequest(BaseModel):
    username: str = Field(..., description = "비밀번호 재설정 대상 username")
    confirmation_code: str = Field(..., description = "사용자에게 발송된 확인 코드")
    new_password: str = Field(..., min_length=8, description = "새로운 비밀번호 (최소 8자 이상)")