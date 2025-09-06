# main.py
# 목적:
# - FastAPI 앱 구성 + app/routers 자동 등록(생략 가능)
# - Mangum으로 Lambda 실행
# - REST API(v1) 이벤트에서 requestContext.authorizer.claims를 읽어
#   request.state.claims로 주입(HTTP API와 경로 다름)

from __future__ import annotations

import logging
import importlib
import pkgutil
from types import ModuleType
from typing import Iterable, Tuple, List, Dict, Any
from fastapi import FastAPI, APIRouter, Request, Response
from mangum import Mangum
import app.routers as routers_package
from app.core.config import OtherSettings

from fastapi.middleware.cors import CORSMiddleware


def _iter_submodules(
    package: ModuleType, base_pkg_name: str
) -> Iterable[Tuple[str, ModuleType]]:
    """
    특정 “패키지 객체”를 시작점으로, 그 하위의 모든 서브모듈과 서브패키지를 재귀적으로 탐색해 import하고,
     “모듈의 전체 경로(str)”와 “모듈 객체(ModuleType)” 쌍을 순차적으로 넘겨줍니다.
     - 패키지인지 확인
     - 하위 나열
     - 모듈 import
     - 재귀 탐색
     - 결과 산출
    """

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
    """
    루트 제거: full_module_name에서 루트 패키지 접두사(root_pkg + ".")를 잘라내,
    순수 하위 경로만 추출합니다. 예: app.routers.files.upload → files.upload
    URL 경로화:
        - 점(.)을 슬래시(/)로 바꾸고 앞에 "/"를 붙여 “/files/upload” 형태로 만듭니다.
        - 마지막에 불필요한 슬래시가 붙지 않도록 rstrip("/")로 정리합니다.
    """
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
    """
    루트 패키지부터 시작해 하위 모든 모듈을 재귀적으로 훑으면서,
     각 모듈에 정의된 APIRouter 인스턴스를 FastAPI 앱에 자동 등록합니다

    1. 루트 패키지 직속 라우터 등록
    2. 하위 모듈 재귀 순회
    """
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
    title="BizLenz API (REST + Cognito User Pools)",
    description="Cognito User Pool Authorizer로 보호되는 REST API. Lambda(FastAPI+Mangum).",
    version="1.0.0",
)


ALLOWED_ORIGINS = OtherSettings.ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # (credentials 사용 시 구체 오리진 권장)
    allow_credentials=True,  # 쿠키/인증정보 포함 요청 허용 시 True
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=86400,
    # 필요 시 브라우저가 읽을 수 있는 헤더를 노출
    # expose_headers=["Content-Disposition"],
)

include_routers_recursive(app, routers_package, "app.routers")
logger = logging.getLogger("bizlenz.auth")  # 인증/인가 영역 전용 로거


# REST API(v1)용: requestContext.authorizer.claims 경로 사용
@app.middleware("http")
async def inject_claims(request: Request, call_next):
    """
    API Gateway REST API(v1)에서 Cognito User Pools Authorizer 통과 후:
    - Lambda 이벤트에 requestContext.authorizer.claims가 존재
    - Mangum이 request.scope['aws.event']로 이벤트를 노출
    """
    claims: Dict[str, Any] = {}
    aws_event = request.scope.get("aws.event")
    # request 객체에서 AWS가 전달한 전체 이벤트 페이로드를 가져오는 과정
    if isinstance(aws_event, dict):
        rc = aws_event.get("requestContext", {})
        authorizer = rc.get("authorizer", {}) or {}
        # REST API는 jwt 중첩 없이 바로 claims 필드인 경우가 일반적
        if isinstance(authorizer, dict):
            # 일부 환경에서 'claims' 속성이 없거나 커스텀 context로 제공될 수 있으니 방어적으로 처리
            claims = authorizer.get("claims") or {}
            # AWS API Gateway (REST API 타입)가 Cognito Authorizer를 통해 요청을 검증하면, requestContext.authorizer.claims 경로에 검증된 JWT의 payload(claims)를 담아줍니다.
            if not claims:
                jwt_obj = authorizer.get("jwt") or {}
                if isinstance(jwt_obj, dict):
                    jwt_claims = jwt_obj.get("claims")
                    if isinstance(jwt_claims, dict) and jwt_claims:
                        claims = jwt_claims
                        logger.debug("Extracted claims from HTTP authorizer.jwt.claims")
        else:
            logger.debug("Unexpected requestContext type: %s", type(rc).__name__)
    else:
        logger.debug("aws.event not found on request.scope or wrong type")

    # cognito:groups 표준화(문자열 -> 리스트, 누락 -> 빈 리스트)
    raw_groups = claims.get("cognito:groups")
    if isinstance(raw_groups, str):
        """
        Cognito는 사용자가 여러 그룹에 속해 있을 경우, 그룹 목록을 콤마(,)로 구분된 단일 문자열로 전달합니다. (예: "admin,user,power-user")
        이 코드는 cognito:groups 값이 문자열이면, 이를 쉼표 기준으로 잘라서 파이썬 리스트 [] 형태로 변환합니다. (예: ['admin', 'user', 'power-user'])
        만약 그룹 정보가 아예 없다면(None), 빈 리스트 []를 할당합니다.
        이렇게 데이터의 형식을 일관되게 만들어주면, 이후 로직에서 if 'admin' in user_groups: 와 같이 타입 걱정 없이 안전하고 편리하게 그룹을 확인할 수 있습니다.
        """
        claims["cognito:groups"] = [
            g.strip() for g in raw_groups.split(",") if g.strip()
        ]
    elif raw_groups is None:
        claims["cognito:groups"] = []

    request.state.claims = claims

    response: Response = await call_next(request)
    # 미들웨어의 본분을 다했으니, call_next를 호출하여 요청을 다음 단계(다른 미들웨어 또는 실제 API 엔드포인트)로 전달합니다.

    return response


# Lambda 핸들러
handler = Mangum(app, lifespan="off")
