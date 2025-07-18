from fastapi.testclient import TestClient
import unittest.mock as mock
from unittest.mock import patch
import pytest
import botocore.exceptions

from app.main import app
client = TestClient(app)

@pytest.fixture
def mock_s3():
    with patch("app.routers.files.s3_client") as mock:
        yield mock 
# 실제 S3 클라이언트에 연결하지 않고, boto3의 s3_client를 모킹하여 s3와의 네트워크 통신 차단.
# 네트워크 요금 발생하지 않음.
# 이 fixture를 통해, s3의 generate_presigned_url과 delete_object 메서드 자유롭게 제어함.

def test_upload_file(mock_s3):
    mock_s3.generate_presigned_url.return_value = "https://dummy-url.com"
    payload = {
        "filename": "test.txt",
        "filetype": "text/plain"
    }

    response = client.post("/upload", json=payload)
    # /upload API가 정상 동작할 때, presinged URL과 file URL이 잘 생성되는지 확인(json 형식을 비교)
    assert response.status_code == 200
    assert "upload_url" in response.json()
    assert "file_url" in response.json()

def test_upload_file_error(mock_s3):
    mock_s3.generate_presigned_url.side_effect = botocore.exceptions.ClientError(
        error_message={
            "Error": {
                "Code": "InternalError",
                "Message": "S3 internal error"
            }
        }
        , operation_name='generate_presigned_url'
    )
    payload = {
        "filename": "test.pdf",
        "filetype": "pdf"
    }

    response = client.post("/upload", json=payload)
    # /upload API가 에러 발생 시, 500 에러 코드와 에러 메시지가 반환되는지 확인
    assert response.status_code == 500
    assert "S3 internal error" in response.json()["detail"]
    
    def test_delete_file(mock_s3):
        mock.s3.delete_object.return_value = {}
        response = client.delete("/uploads/test.txt")
        # /delete API가 정상 동작할 때, 파일 삭제 성공 메시지가 반환되는지 확인
        assert response.status_code == 200
        assert response.json() == {"message": "File deleted successfully"}  

    def test_delete_file_error(mock_s3):
        mock.s3.delete_object.side_effect = botocore.exceptions.ClientError(
            error_message={
                "Error": {
                    "Code": "AccessDenied",
                    "Message": "You do not have permission to access this resource"
                }
            },
            operation_name='delete_object'
        )
        response = client.delete("/uploads/test.pdf")
        # /delete API가 에러 발생 시, 500 에러 코드와 에러 메시지가 반환되는지 확인
        assert response.status_code == 403
        assert "permission to access this resource" in response.json()["detail"].lower()

