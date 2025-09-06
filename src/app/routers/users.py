from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from app.core.security import require_scope


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