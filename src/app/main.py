import importlib
import pkgutil
from fastapi import FastAPI, APIRouter
from mangum import Mangum
from types import ModuleType
from typing import Iterable, List


# app.routers 패키지를 별칭으로 임포트하여 충돌 방지
import app.routers as routers_package

def _iter_submodules(packages: ModuleType, base_pkg_name: str) -> Iterable[tuple[str, ModuleType]]:
    """
    주어진 패키지의 모든 서브모듈을 재귀적으로 순회하며 (폴 모듈 경로, 모듈 객체) 튜플을 생성합니다.
    """
    for finder, name, is_pkg in pkgutil.iter_modules(package.__path__):
        full_module_name = f"{base_pkg_name}.{name}"
        
        if is_pkg:
            # 패키지 자체도 반환하지 않고, 그 안의 모듈들을 재귀적으로 순회
            # (패키지 모듈에 APIRouter가 있을 수 있다면, 필요 시 아래에서 yield 추가 가능)
            yield from _iter_submodules(module, full_module_name)
        else:
            # 일반 모듈은 반환
            yield full_module_name, module

def _module_to_prefix(full_module_name: str, root_pkg: str) -> str:
    """
    풀 모듈 경로에서 루트 패키지명을 제거하고 URL prefix로 변환
    예:
      full_module_name="app.routers.files.upload"
      root_pkg="app.routers"
      -> "/files/upload"

      full_module_name="app.routers.health"
      -> "/health"
    """
    # 접두사 제거
    if full_module_name.startswith(root_pkg+"."):
        trimmed = full_module_name[len(root_pkg)+1:]
    else:
        trimmed = full_module_name

     # 점(.)을 슬래시(/)로 치환하여 URL 경로 생성
    parts: List[str] = trimmed.split(".")
    return "/" + "/".join(parts)

    def include_routers_recursive(app:FastAPI, root_pkg: ModuleType, root_pkg_name: str) -> None:
    """
    루트 패키지부터 시작해 모든 하위 모듈을 재귀 탐색하고,
    각 모듈에서 발견되는 APIRouter 인스턴스를 FastAPI 앱에 등록합니다.
    """
    # 루트 패키지 모듈에 정의된 APIRouter를 먼저 등록
    for attr_name in dir(root_pkg):
        attr = getattr(root_pkg, attr_name)
        if isinstance(attr, APIRouter):
            prefix = "/"
            app.include_router(attr, prefix=prefix, tags =["root"])
            print(f"[Router] {root_pkg_name}.{attr_name} -> prefix='{prefix}', tags=['root']")
    
    # 하위 모듈 / 패키지 재귀 순회
    for full_module_name, module in _iter_submodules(root_pkg, root_pkg_name):
        # 모듈 내 정의된 모든 APIRouter 탐색
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, APIRouter):
                prefix = _module_to_prefix(full_module_name, root_pkg_name)
                # 태그는 마지막 경로 조각을 사용 (예: upload, users 등)
                tag = prefix.strip("/").split("/")[-1] or "root"
                app.include_router(attr, prefix=prefix, tags=[tag])
                print(f"[Router] {full_module_name}.{attr_name} -> prefix='{prefix}', tags=['{tag}']")



# FastAPI 앱 생성 시 상세한 메타데이터 추가
app = FastAPI(
    title="BizLenz File Service API",
    description="""
    BizLenz File Service API는 사용자가 제출한 사업계획서 파일을 업로드, 분석, 관리하는 기능을 제공합니다.
    비즈니스 모델 캔버스 생성 및 평가 기준에 맞춘 피드백 기능과 연동됩니다.
    """,
    version="1.0.0",
    terms_of_service="https://bizlenz.example.com/terms/",
    contact={
        "name": "BizLenz 개발팀",
        "url": "https://bizlenz.example.com/contact/",
        "email": "support@bizlenz.example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }
)


# 라우터 자동 등록
include_routers(app, "app.routers", routers_package)

# AWS Lambda 진입점
handler = Mangum(app)
