<p align="center">
  <picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/BizLenz/.github/refs/heads/main/assets/logo/logo_dark.svg">
  <img src="https://raw.githubusercontent.com/BizLenz/.github/refs/heads/main/assets/logo/logo_light.svg" width="130" alt="Logo for BizLenz">
</picture>
</p>

<h1 align="center">
  BizLenz
</h1>

<p align="center">
  AI-powered business proposal analysis tool for the web
</p>

> BizLenz는 과학기술정보통신부 대학디지털교육역량강화사업의 지원을 통해 수행한 한이음 드림업 프로젝트 결과물입니다.

## api
API for BizLenz.

### Usage

[uv](https://github.com/astral-sh/uv) is required to run the app.
See Makefile for details.

```bash
make dev       # run the app in development mode
make format    # format code (uses ruff)
make lint      # lint code (uses ruff)
make test      # test code (uses pytest)
make clean     # clean up build files and cache
```

### Architecture

<img src="https://raw.githubusercontent.com/BizLenz/.github/refs/heads/main/assets/architecture/api_architecture.svg" alt="api_architecture" width="400"/>

The backend was developed using the FastAPI framework to ensure seamless integration with AI systems.
