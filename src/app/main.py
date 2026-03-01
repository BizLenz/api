from __future__ import annotations

import logging
import importlib
import os
import pkgutil
from types import ModuleType
from typing import Iterable, Tuple, List, Dict, Any
from fastapi import FastAPI, APIRouter, Request, Response
import app.routers as routers_package
from .health import health_router
from app.core.config import settings

from fastapi.middleware.cors import CORSMiddleware

from app.middleware.oidc_auth import OIDCAuthMiddleware


def _iter_submodules(
    package: ModuleType, base_pkg_name: str
) -> Iterable[Tuple[str, ModuleType]]:
    if not hasattr(package, "__path__"):
        return
    for _, name, is_pkg in pkgutil.iter_modules(package.__path__):
        full = f"{base_pkg_name}.{name}"
        module = importlib.import_module(full)
        if is_pkg:
            yield from _iter_submodules(module, full)
        else:
            yield full, module


def _module_to_prefix(full_module_name: str, root_pkg: str) -> str:
    trimmed = (
        full_module_name[len(root_pkg) + 1 :]
        if full_module_name.startswith(root_pkg + ".")
        else full_module_name
    )
    parts: List[str] = [p for p in trimmed.split(".") if p]
    prefix = "/" + "/".join(parts)
    return prefix.rstrip("/") if prefix != "/" else "/"


def include_routers_recursive(
    app: FastAPI, root_pkg: ModuleType, root_pkg_name: str
) -> None:
    for attr_name in dir(root_pkg):
        attr = getattr(root_pkg, attr_name)
        if isinstance(attr, APIRouter):
            app.include_router(attr, prefix="/", tags=["root"])
    for full, module in _iter_submodules(root_pkg, root_pkg_name):
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, APIRouter):
                prefix = _module_to_prefix(full, root_pkg_name)
                tag = prefix.strip("/").split("/")[-1] or "root"
                app.include_router(attr, prefix=prefix, tags=[tag])


app = FastAPI(
    title="BizLenz API",
    description="AI-powered business plan analysis API.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=86400,
)

# Generic OIDC auth middleware; only activated when AUTH_JWKS_URL is configured.
if settings.auth_jwks_url:
    app.add_middleware(
        OIDCAuthMiddleware,
        jwks_url=settings.auth_jwks_url,
        issuer=settings.auth_issuer or "",
        audience=settings.auth_audience or "",
    )

include_routers_recursive(app, routers_package, "app.routers")
app.include_router(health_router)

logger = logging.getLogger("bizlenz.auth")


@app.middleware("http")
async def inject_claims(request: Request, call_next):
    """Normalise JWT claims set by OIDCAuthMiddleware on the request state"""
    claims: Dict[str, Any] = getattr(request.state, "claims", {})

    # Normalise groups claim: support both list and comma-separated string.
    raw_groups = claims.get("groups")
    if isinstance(raw_groups, str):
        claims["groups"] = [g.strip() for g in raw_groups.split(",") if g.strip()]
    elif raw_groups is None:
        claims["groups"] = []

    request.state.claims = claims

    response: Response = await call_next(request)
    return response


# Lambda handler; only created when running inside AWS Lambda.
if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    from mangum import Mangum

    handler = Mangum(app, lifespan="off")
