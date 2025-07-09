FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install uv && uv sync

CMD ["uv", "run", "python", "calculator.py"]
