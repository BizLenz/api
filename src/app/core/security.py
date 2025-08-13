# 목적: FastAPI 라우트에서 공통으로 사용하는 인증/인가 의존성 함수 제공
# - get_claims: 미들웨어가 주입한 request.state.claims를 꺼내 인증 보장
# - require_scope: OAuth2 스코프(bizlenz.read/write 등) 확인하여 인가 보장


from typing import Dict, Any, List
from fastapi import Depends, HTTPException, Request, status

def get_claims(request: Request) -> Dict[str, Any]:
    """
    미들웨어에서 request.state.claims로 주입한 JWT 클레임을 반환합니다.
    sub가 없거나 비어 있으면 인증 실패(401)로 처리합니다.
    """
    claims = getattr(request.state, "claims", None)
    if not isinstance(claims, dict) or "sub" not in claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return claims

def parse_scopes_from_claims(claims: Dict[str, Any]) -> List[str]:
    """
    공급자별로 scope 또는 scp로 들어오는 스코프를 표준화하여 리스트로 변환합니다.
    - scope: "a b c" 같은 공백 구분 문자열인 경우가 많음
    - scp: 배열/문자열 등 공급자마다 다를 수 있어 방어적으로 처리
    """
    raw = claims.get("scope")
    if isinstance(raw, str):
        return [s for s in raw.split() if s]
    if isinstance(raw, list):
        return [str(s) for s in raw if s]

    raw_scp = claims.get("scp")
    if isinstance(raw_scp, str):
        return [s for s in raw_scp.split() if s]
    if isinstance(raw_scp, list):
        return [str(s) for s in raw_scp if s]
    return []

def require_scope(required: str):
    """
    특정 스코프(required)가 있어야 라우트 접근을 허용하는 의존성 팩토리.
    사용 예:
      @router.get("/me")
      def me(claims: Dict = Depends(require_scope("bizlenz.read"))): ...
    """
    def checker(claims: Dict[str, Any] = Depends(get_claims)) -> Dict[str, Any]:
        scopes = parse_scopes_from_claims(claims)
        if required not in scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing scope: {required}")
        return claims
    return checker

def get_groups(claims: Dict[str, Any]) -> List[str]:
    """
    cognito:groups를 문자열/리스트 모두 지원하도록 표준화합니다.
    미들웨어에서 표준화했더라도, 방어적으로 한 번 더 변환합니다.
    """
    raw = claims.get("cognito:groups")
    if isinstance(raw, list):
        return [str(g) for g in raw if str(g).strip()]
    if isinstance(raw, str):
        return [g.strip() for g in raw.split(",") if g.strip()]
    return []