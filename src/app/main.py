from fastapi import FastAPI
from src.app.routers.files import files 


app= FastAPI()
app.include_router(files.router)
