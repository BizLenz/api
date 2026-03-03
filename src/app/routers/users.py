from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from app.core.security import require_scope, get_groups


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def get_me(claims: Dict[str, Any] = Depends(require_scope("bizlenz/read"))):
    groups: List[str] = get_groups(claims)
    user = {
        "id": claims["sub"],
        "sub": claims["sub"],
        "email": claims.get("email"),
        "role": "editor",
        "groups": groups,
    }
    return {"me": user}
