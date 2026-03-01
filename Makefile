.PHONY: format lint test test-ci clean dev

UV_RUN := uv run

dev:
	$(UV_RUN) uvicorn app.main:app --reload

format:
	$(UV_RUN) ruff format src/
	$(UV_RUN) ruff check --fix src/

lint:
	$(UV_RUN) ruff check src/

# Run tests with optional test extras installed
test:
	uv sync --extra test
	CI=true $(UV_RUN) pytest

# Same but explicit for CI environments
test-ci:
	uv pip install -r requirements.txt
	CI=true $(UV_RUN) pytest

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
