# 파이썬 베이스 이미지 사용
FROM python:3.11-slim

# 작업 디렉터리 설정
WORKDIR /app

# pyproject.toml 파일을 먼저 복사
COPY pyproject.toml .

# uv 설치 및 종속성 동기화
RUN pip install uv && uv sync

# 나머지 코드 복사
COPY . .

# uv run을 사용하여 uvicorn을 실행
# 이렇게 하면 uv가 올바른 환경에서 uvicorn을 찾아 실행합니다.
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]