FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install uv && uv sync

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# uvicorn	FastAPI 앱을 실행하는 ASGI 서버입니다. Python 서버 실행기 중 하나
# app.main:app	app/main.py 안에 있는 FastAPI 인스턴스를 지정한 것
#     → app 디렉토리의 main.py에 정의된 app = FastAPI() 인스턴스를 실행하라는 뜻
# --host 0.0.0.0	모든 외부 IP 요청을 받아들일 수 있게 설정
#        → Docker 내부 서버를 외부에서 접근 가능하게 만듦
# --port 8000	FastAPI 서버가 열릴 포트 번호
#     → 즉, http://localhost:8000 으로 접근 가능하게 됨