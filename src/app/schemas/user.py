# src/app/schemas/user.py

from pydantic import BaseModel, EmailStr
from datetime import datetime

# 공통 속성
class UserBase(BaseModel):
    email: EmailStr

# 회원가입 요청
class UserCreate(UserBase):
    password: str

# 로그인 요청
class UserLogin(UserBase):
    password: str

# 응답 반환
class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

# 내부 처리용 (DB와 상호작용할 때 사용)
class UserInDB(UserBase):
    id: int
    hashed_password: str
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True
