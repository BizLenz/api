"""
Generic OIDC JWT authentication middleware

Configure via AUTH_JWKS_URL, AUTH_ISSUER, and AUTH_AUDIENCE environment variables
"""

from typing import Dict, Any, List, Union

import httpx
from fastapi import Request, HTTPException, status
from jose import jwt, JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

_cached_jwks: Dict[str, Any] = {}


class OIDCAuthMiddleware(BaseHTTPMiddleware):
    """
    Validates Bearer JWT tokens against a configurable JWKS endpoint

    Populates request.state.claims with the decoded token payload on success
    Requests without an Authorization header are passed through unchanged
    """

    def __init__(
        self,
        app,
        jwks_url: str,
        issuer: str,
        audience: Union[str, List[str]],
    ):
        super().__init__(app)
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.audience = audience if isinstance(audience, str) else audience[0]

    async def _fetch_jwks(self) -> Dict[str, Any]:
        global _cached_jwks
        if _cached_jwks.get(self.jwks_url):
            return _cached_jwks[self.jwks_url]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                _cached_jwks[self.jwks_url] = response.json()
                return _cached_jwks[self.jwks_url]
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not fetch JWKS: {e.response.status_code}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not fetch JWKS: {e}",
            )

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return await call_next(request)

        token = auth_header.split(" ", 1)[1]

        try:
            jwks = await self._fetch_jwks()
            decoded = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"verify_at_hash": False},
            )
            request.state.claims = decoded
        except JWTError as e:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": f"Invalid or expired token: {e}"},
            )
        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Authentication error"},
            )

        return await call_next(request)
