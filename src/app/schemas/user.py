from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
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



