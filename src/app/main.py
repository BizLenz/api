from fastapi import FastAPI
from app.routers.files import files 


app= FastAPI()
app.include_router(files.router)
