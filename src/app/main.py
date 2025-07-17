from fastapi import FastAPI

app= FastAPI()

from src.app.routers.files import files 

app.include_router(files.router)
