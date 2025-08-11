import importlib
import pkgutil
from fastapi import FastAPI, APIRouter
from mangum import Mangum

# app.routers 패키지를 별칭으로 임포트하여 충돌 방지
import app.routers as routers_package

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

def include_routers(app: FastAPI, package_name: str, package) -> None:
    """
    지정한 패키지 내 모든 모듈을 탐색하여 APIRouter 인스턴스를 앱에 등록합니다.
    :param app: FastAPI 인스턴스
    :param package_name: 예) "app.routers" (문자열 패키지 이름)
    :param package: 임포트된 패키지 객체 (예: app.routers)
    """
    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
        if is_pkg:
            continue  # 하위 패키지는 무시
        full_module_name = f"{package_name}.{module_name}"
        module = importlib.import_module(full_module_name)

        # 모듈 내 모든 속성 탐색
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            # APIRouter 객체라면 FastAPI에 include
            if isinstance(attr, APIRouter):
                # files 모듈은 prefix 그대로 /files, 나머지는 모듈명으로 prefix 지정
                prefix = f"/{module_name}"
                app.include_router(attr, prefix=prefix, tags=[module_name])
                print(f"Router included: {full_module_name}.{attr_name} with prefix '{prefix}'")

# 라우터 자동 등록
include_routers(app, "app.routers", routers_package)

# AWS Lambda 진입점
handler = Mangum(app)
