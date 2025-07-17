import os
import boto3
from uuid import uuid4
from fastapi import FastAPI() HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

files = FastAPI()

# AWS S3 클라이언트 설정
s3_client = boto3.client(
    's3',
    region_name=os.getenv('AWS_REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    S3_BUCKET=os.getenv('S3_BUCKET')
)
#pydantic 모델의 요청 형식 정의
class FileUploadRequest(BaseModel):  
    filename: str
    filetype: str

@files.post("/upload") 
async def upload_file(file: FileUploadRequest):
    try:
        key = f"uploads/{uuid4()}_{file.filename}"
        url = s3_client.generate_presigned_url(    
            'put_object', # S3에 파일 업로드 명령어
            Params={ #버킷 파라미터
                'Bucket':S3_BUCKET,
                'Key': key,
                'ContentType': file.filetype
            },
            ExpiresIn=300 #5분 유효
        )
        return {
            "upload_url": url, # presigned URL 반환
            "file_url": f"https://{S3_BUCKET}.s3.amazonaws.com/{key}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  # 에러 발생 시 500 에러 반환
@files.delete("/{key:path}")
async def delete_file(key: str):
    try:
        s3_client.delete_object(Bucket=os.getenv('S3_BUCKET'), Key=key) #제공된 키와 버킷 이름을 통해 delete_object 메서드 호출 
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))