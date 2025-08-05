from fastapi import FastAPI
from app.routers.files import files
from mangum import Mangum

app = FastAPI()
app.include_router(files.router)

handler = Mangum(app)
