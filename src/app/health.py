from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
import time

health_router = APIRouter()

START_TIME = time.time()

@health_router.get("/healthz", status_code=status.HTTP_200_OK, tags=["health"])
async def health_check():
    uptime = time.time() - START_TIME
    return JSONResponse(
        content={"status": "healthy", "uptime": uptime}
    )