import os
import boto3
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from botocore.exceptions import ClientError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from dotenv import load_dotenv

load_dotenv()
# .env 파일에서 환경 변수 로드
required_env_vars = [
    'AWS_REGION',
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY',
    'S3_BUCKET'
]
# 오류 체크
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

files = FastAPI()

origins = [
    "http://localhost:3000",  # 로컬 개발 환경
]

files.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # CORS 허용할 오리진 설정
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# AWS S3 클라이언트 설정
s3_client = boto3.client(
    's3',
    region_name=os.getenv('AWS_REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
)


# pydantic 모델의 요청 형식 정의
class FileUploadRequest(BaseModel):
    filename: str
    filetype: str

    # 파일 타입 체킹
    @validator('filetype')
    def validate_filetype(cls, v):
        if v.lower() != 'pdf':
            raise ValueError('Not supplied file type')
        return v


def type_s3_exception(e: Exception):
    if isinstance(e, ClientError):
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        if error_code in ["NoSuchKey", "NotFound"]:
            raise HTTPException(status_code=404, detail=error_message)
        elif error_code in ["AccessDenied"]:
            raise HTTPException(status_code=403, detail=error_message)
        elif error_code in ["InvalidRequest"]:
            raise HTTPException(status_code=400, detail=error_message)
        else:
            raise HTTPException(status_code=500, detail=error_message)
    else:
        raise HTTPException(status_code=500, detail=str(e))


@files.post("/upload")
async def upload_file(file: FileUploadRequest):
    try:
        key = f"uploads/{uuid4()}_{file.filename}"
        url = s3_client.generate_presigned_url(
            'put_object',  # S3에 파일 업로드 명령어
            Params={  # 버킷 파라미터
                'Bucket': os.getenv('S3_BUCKET'),
                'Key': key,
                'ContentType': file.filetype
            },
            ExpiresIn=300  # 5분 유효
        )
        return {
            "upload_url": url,  # presigned URL 반환
            "file_url": f"https://{os.getenv('S3_BUCKET')}.s3.amazonaws.com/{key}"
        }
    except Exception as e:
        raise type_s3_exception(e)


@files.delete("/{key:path}")
async def delete_file(key: str):
    try:
        s3_client.delete_object(Bucket=os.getenv('S3_BUCKET'), Key=key)  # 제공된 키와 버킷 이름을 통해 delete_object 메서드 호출
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise type_s3_exception(e)
