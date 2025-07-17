FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .  # ← 이 줄을 반드시 추가!
# COPY poetry.lock .   # 만약 사용하는 경우


RUN pip install uv && uv sync

# 앱 코드 복사 (이 시점 이후에)
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
