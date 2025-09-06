import json
from typing import Dict, Any, List, Union
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import jwt, JWTError
import httpx


_cached_jwks_keys: Dict[str, Any] = {}


class CognitoAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        user_pool_id: str,
        region: str,
        audience: Union[str, List[str]],
    ):
        super().__init__(app)
        self.user_pool_id = user_pool_id
        self.region = region

        if isinstance(audience, str):
            self.expected_audience_for_jwt_decode = audience
        elif isinstance(audience, list) and len(audience) == 1:
            self.expected_audience_for_jwt_decode = audience[
                0
            ]  # Take the single string from the list
        else:
            raise ValueError(
                "Middleware configured with invalid 'audience'. Must be a single string."
            )

        self.original_audience_config = audience

        self.jwks_url = (
            f"https://cognito-idp.{self.region}.amazonaws.com/"
            f"{self.user_pool_id}/.well-known/jwks.json"
        )
        self.jwks_client = None

    async def _fetch_jwks(self):
        global _cached_jwks_keys
        if _cached_jwks_keys.get(self.user_pool_id):
            return _cached_jwks_keys[self.user_pool_id]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                _cached_jwks_keys[self.user_pool_id] = response.json()
                return _cached_jwks_keys[self.user_pool_id]
        except httpx.HTTPStatusError as e:
            print(
                f"Error fetching JWKS: HTTPStatusError - {e.response.status_code}: {e.response.text}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not fetch public keys for token validation.",
            )
        except Exception as e:
            print(f"Error fetching JWKS: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not fetch public keys for token validation.",
            )

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return await call_next(request)

        token = auth_header.split(" ")[1]

        try:
            jwks = await self._fetch_jwks()

            issuer = (
                f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
            )

            print("\n--- CognitoAuthMiddleware Debug ---")
            print(f"Token received: {token[:30]}...")
            print(f"Expected Issuer: {issuer}")
            # Log the actual type being used for audience in jwt.decode
            print(
                f"Expected Audience (for jwt.decode): {self.expected_audience_for_jwt_decode} (Type: {type(self.expected_audience_for_jwt_decode)})"
            )

            decoded_token = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience=self.expected_audience_for_jwt_decode,
                issuer=issuer,
                options={"verify_at_hash": False},
            )

            print("Token Decoded Successfully. Claims:")
            print(json.dumps(decoded_token, indent=2))
            print("--- End CognitoAuthMiddleware Debug ---\n")

            request.state.claims = decoded_token

        except JWTError as e:
            print("--- CognitoAuthMiddleware JWTError ---")
            print(f"JWT Validation Failed: {e}")
            print("--- End CognitoAuthMiddleware JWTError ---\n")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=f"Invalid or expired token: {e}",
            )
        except HTTPException as e:
            print("--- CognitoAuthMiddleware HTTPException ---")
            print(f"Middleware setup error: {e.detail}")
            print("--- End CognitoAuthMiddleware HTTPException ---\n")
            return JSONResponse(status_code=e.status_code, content=e.detail)
        except Exception as e:
            print("--- CognitoAuthMiddleware General Error ---")
            print(f"Unhandled error during token processing: {e}")
            print("--- End CognitoAuthMiddleware General Error ---\n")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content="Authentication server error.",
            )

        response = await call_next(request)
        return response
