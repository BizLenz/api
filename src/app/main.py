# src/app/main.py
from fastapi import FastAPI
from app.routers import files

app = FastAPI()

app.include_router(files.router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
