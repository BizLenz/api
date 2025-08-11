# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.files import files  # 파일 API 라우터 임포트 (예시)
# 다른 라우터도 필요에 따라 추가

app = FastAPI()

# CORS 정책 설정
origins = [
    "http://localhost:3000",  # 개발용 프론트엔드 오리진
    # "https://mybizlenz.com", # 실제 서비스 도메인도 필요 시 추가
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           # 허용할 오리진 리스트
    allow_credentials=True,
    allow_methods=["*"],             # 모든 HTTP 메서드 허용
    allow_headers=["*"],             # 모든 헤더 허용
)

# 라우터 등록
app.include_router(files, prefix="/files")  # 파일 업로드 등 api
