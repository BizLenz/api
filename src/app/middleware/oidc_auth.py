"""
Generic OIDC JWT authentication middleware

Configure via AUTH_JWKS_URL, AUTH_ISSUER, and AUTH_AUDIENCE environment variables
"""

import logging
from time import monotonic
from typing import Dict, Any, List, Union

import httpx
from fastapi import Request, HTTPException, status
from jose import jwt, JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# url -> (jwks_data, fetched_at_monotonic)
_JWKS_CACHE: Dict[str, tuple] = {}
JWKS_CACHE_TTL = 300  # seconds


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
        entry = _JWKS_CACHE.get(self.jwks_url)
        if entry and (monotonic() - entry[1]) < JWKS_CACHE_TTL:
            return entry[0]

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                data = response.json()
                _JWKS_CACHE[self.jwks_url] = (data, monotonic())
                return data
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not fetch JWKS: {e.response.status_code}",
            )
        except Exception:
            logger.exception("Unexpected error fetching JWKS from %s", self.jwks_url)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not fetch JWKS",
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
        except JWTError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
            )
        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
        except Exception:
            logger.exception("Unexpected authentication error")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Authentication error"},
            )

        return await call_next(request)
