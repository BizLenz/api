name: CI

on:
  push:
    branches: [ "main", "feature/**" ]
  pull_request:
    branches: [ "main", "feature/**" ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Install Python 3.11 with uv
        run: uv python install 3.11

      - name: Sync dependencies
        run: uv sync

      - name: Create .env file (from ENV_FILE secret)
        run: echo "${{ secrets.ENV_FILE }}" | tr '\n' '\n' > .env

      - name: Install uv audit
        run: uv pip install uv-audit

      - name: Create .env file (AWS credentials)
        run: |
          echo "S3_BUCKET=${{ secrets.S3_BUCKET }}" > .env
          echo "AWS_ACCESS_KEY_ID=${{ secrets.AWS_ACCESS_KEY_ID }}" >> .env
          echo "AWS_SECRET_ACCESS_KEY=${{ secrets.AWS_SECRET_ACCESS_KEY }}" >> .env
          echo "AWS_REGION=${{ secrets.AWS_REGION }}" >> .env

      - name: Ruff Lint
        uses: astral-sh/ruff-action@v3
        with:
          args: check --output-format=github .

      - name: Ruff Fix
        run: ruff format .

      - name: Ruff Format Check
        uses: astral-sh/ruff-action@v3
        with:
          args: format --check .

      - name: Run uv audit
        run: uv run uv-audit

      - name: Run Pytest
        run: uv run pytest

      - name: Build Docker image
        run: docker build -t my-app:${{ github.sha }} .
