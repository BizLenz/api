from typing import Dict, Any, List
from fastapi import Depends, HTTPException, Request, status


def get_claims(request: Request) -> Dict[str, Any]:
    """
    Return JWT claims injected by the auth middleware into request.state.claims
    Raises 401 if no authenticated claims are present
    """
    claims = getattr(request.state, "claims", None)
    if not isinstance(claims, dict) or not claims.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    return claims


def parse_scopes_from_claims(claims: Dict[str, Any]) -> List[str]:
    """
    Normalise OAuth2 scopes from either the 'scope' or 'scp' claim
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
    Dependency factory; allow access only if the JWT contains the required scope

    Usage:
        @router.get("/me")
        def me(claims: Dict = Depends(require_scope("bizlenz/read"))): ...
    """

    def checker(claims: Dict[str, Any] = Depends(get_claims)) -> Dict[str, Any]:
        scopes = parse_scopes_from_claims(claims)
        if required not in scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing scope: {required}",
            )
        return claims

    return checker


def get_groups(claims: Dict[str, Any]) -> List[str]:
    """
    Extract the 'groups' claim from a JWT payload
    """
    raw = claims.get("groups")
    if isinstance(raw, list):
        return [str(g) for g in raw if str(g).strip()]
    if isinstance(raw, str):
        return [g.strip() for g in raw.split(",") if g.strip()]
    return []
