.PHONY: format lint test clean

UV_RUN := uv run

dev:
	$(UV_RUN) uvicorn app.main:app --reload

format:
	$(UV_RUN) ruff format src/
	$(UV_RUN) ruff check --fix src/

lint:
	$(UV_RUN) ruff check src/

test:
	$(UV_RUN) pytest

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete