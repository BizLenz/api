# src/app/main.py

import importlib
import pkgutil
from fastapi import FastAPI, APIRouter
from mangum import Mangum

# app.routers 모듈을 별칭으로 임포트 (변수명 중복 방지)
import app.routers as routers_package

app = FastAPI(title="BizLenz File Service API")


def include_routers(app: FastAPI, package_name: str, package):
    """
    package_name: 예) "app.routers"
    package: 예) app.routers 모듈 객체
    """
    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
        if is_pkg:
            continue  # 하위 패키지 무시
        full_module_name = f"{package_name}.{module_name}"
        module = importlib.import_module(full_module_name)

        # 모듈 내 APIRouter 인스턴스 탐색 및 등록
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, APIRouter):
                prefix = "/" + module_name if module_name != "files" else "/files"
                app.include_router(attr, prefix=prefix, tags=[module_name])
                print(f"Router included: {full_module_name}.{attr_name} with prefix '{prefix}'")


include_routers(app, "app.routers", routers_package)

handler = Mangum(app)
