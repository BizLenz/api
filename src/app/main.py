# main.py
import importlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.files import files  # 파일 API 라우터 임포트 (예시)
from mangum import Mangum
import pkgutil
# 다른 라우터도 필요에 따라 추가

app = FastAPI(title="BizLenz File Service API")

# routers 디렉토리(패키지) 경로 지정
import app.routers  

# routers 디렉토리 안 모든 모듈을 자동 임포트하여 APIRouter 객체를 찾아 등록하는 함수
def include_routers(app: FastAPI, package_name: str, package):
    """
    package_name: 예) "app.routers"
    package: 예) app.routers 모듈 객체
    """
    # routers 디렉토리 내 모든 모듈 탐색
    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
        if is_pkg:
            continue  # 하위 패키지 무시
        full_module_name = f"{package_name}.{module_name}"
        module = importlib.import_module(full_module_name)

        # 각 모듈 내에 APIRouter 객체가 'router' 또는 'files'(예시)에 할당된 경우 찾아서 등록
        # "files" 라우터 이름은 실제 라우터 변수명에 맞게 추가 또는 수정 가능
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            # APIRouter 인스턴스 여부 확인
            from fastapi import APIRouter
            if isinstance(attr, APIRouter):
                # prefix는 라우터 변수명과 같거나, 필요시 커스텀으로 지정 가능
                prefix = "/" + module_name if module_name != "files" else "/files"
                app.include_router(attr, prefix=prefix, tags=[module_name])
                print(f"Router included: {full_module_name}.{attr_name} with prefix '{prefix}'")

# routers 디렉토리 내 모든 라우터 등록
include_routers(app, "app.routers", app.routers)

handler = Mangum(app)

