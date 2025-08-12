from fastapi.testclient import TestClient
import unittest.mock as mock
from unittest.mock import patch
import pytest
import botocore.exceptions
import datetime

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_s3():
    with patch("app.routers.files.s3_client") as mock:
        yield mock
<<<<<<< HEAD
    ##!! MOCK !!
=======
>>>>>>> d8f36259897a5fbeb61373e36cb592536ec5bbdd


def test_upload_file(mock_s3):
    mock_s3.generate_presigned_url.return_value = "https://dummy-url.com"
<<<<<<< HEAD
    payload = {
        "filename": "test.pdf",
        "filetype": "pdf"
    }

    response = client.post("/upload", json=payload)
    # /upload API가 정상 동작할 때, presinged URL과 file URL이 잘 생성되는지 확인(json 형식을 비교)
=======
    payload = {"filename": "test.pdf", "filetype": "pdf"}

    response = client.post("/upload", json=payload)
>>>>>>> d8f36259897a5fbeb61373e36cb592536ec5bbdd
    assert response.status_code == 200
    assert "upload_url" in response.json()
    assert "file_url" in response.json()


def test_upload_file_error(mock_s3):
    mock_s3.generate_presigned_url.side_effect = botocore.exceptions.ClientError(
        error_response={
<<<<<<< HEAD
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
=======
            "Error": {"Code": "InternalError", "Message": "S3 internal error"}
        },
        operation_name="generate_presigned_url",
    )
    payload = {"filename": "test.pdf", "filetype": "pdf"}

    response = client.post("/upload", json=payload)
>>>>>>> d8f36259897a5fbeb61373e36cb592536ec5bbdd
    assert response.status_code == 500
    assert "S3 internal error" in response.json()["detail"]

    def test_delete_file(mock_s3):
        mock.s3.delete_object.return_value = {}
        response = client.delete("/uploads/test.txt")
<<<<<<< HEAD
        # /delete API가 정상 동작할 때, 파일 삭제 성공 메시지가 반환되는지 확인
=======
>>>>>>> d8f36259897a5fbeb61373e36cb592536ec5bbdd
        assert response.status_code == 200
        assert response.json() == {"message": "File deleted successfully"}

    def test_delete_file_error(mock_s3):
        mock.s3.delete_object.side_effect = botocore.exceptions.ClientError(
            error_response={
                "Error": {
                    "Code": "AccessDenied",
<<<<<<< HEAD
                    "Message": "You do not have permission to access this resource"
                }
            },
            operation_name='delete_object'
        )
        response = client.delete("/uploads/test.pdf")
        # /delete API가 에러 발생 시, 500 에러 코드와 에러 메시지가 반환되는지 확인
        assert response.status_code == 403
        assert "permission to access this resource" in response.json()["detail"].lower()

=======
                    "Message": "You do not have permission to access this resource",
                }
            },
            operation_name="delete_object",
        )
        response = client.delete("/uploads/test.pdf")
        assert response.status_code == 403
        assert "permission to access this resource" in response.json()["detail"].lower()


>>>>>>> d8f36259897a5fbeb61373e36cb592536ec5bbdd
mock_s3_files = {
    "Contents": [
        {
            "Key": "uploads/test1.pdf",
            "LastModified": datetime.datetime(2023, 10, 1, 12, 0, 0),
<<<<<<< HEAD
            "Size": 123456
=======
            "Size": 123456,
>>>>>>> d8f36259897a5fbeb61373e36cb592536ec5bbdd
        },
        {
            "Key": "uploads/test2.pdf",
            "LastModified": datetime.datetime(2023, 10, 2, 12, 0, 0),
<<<<<<< HEAD
            "Size": 654321
=======
            "Size": 654321,
>>>>>>> d8f36259897a5fbeb61373e36cb592536ec5bbdd
        },
        {
            "Key": "uploads/test3.pdf",
            "LastModified": datetime.datetime(2023, 10, 3, 12, 0, 0),
<<<<<<< HEAD
            "Size": 789012
        }
    ]
}

=======
            "Size": 789012,
        },
    ]
}


>>>>>>> d8f36259897a5fbeb61373e36cb592536ec5bbdd
@patch("app.routers.files.s3_client.list_objects_v2")
def test_select_files(mock_list_objects):
    mock_list_objects.return_value = mock_s3_files
    response = client.get("/select", params={"page": 1, "limit": 2})
<<<<<<< HEAD
    
    # /select API가 정상 동작할 때, 파일 목록이 반환되는지 확인
=======

>>>>>>> d8f36259897a5fbeb61373e36cb592536ec5bbdd
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
<<<<<<< HEAD
    assert len(data["data"]) == 2 # limit 대로 파일 갯수를 잘라서 반환하는지 확인
=======
    assert len(data["data"]) == 2
>>>>>>> d8f36259897a5fbeb61373e36cb592536ec5bbdd
    assert data["pagination"]["current_page"] == 1
    assert data["pagination"]["total_files"] == 3


def test_search_files(mock_s3):
    mock_s3.list_objects_v2.return_value = mock_s3_files
    response = client.get("/search", params={"keywords": "test1", "extension": "pdf"})
<<<<<<< HEAD
    
    # /search API가 정상 동작할 때, 검색 결과가 반환되는지 확인
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1  # test1 단 하나의 파일이 검색 결과에 포함되어야 함
    assert data[0]["file_name"] == "uploads/test1.pdf" # 파일 명이 예상대로인지 확인
    assert data[0]["size"] == 123456 # 사이즈도 맞는 지 확인 
    
=======

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["file_name"] == "uploads/test1.pdf"
    assert data[0]["size"] == 123456
>>>>>>> d8f36259897a5fbeb61373e36cb592536ec5bbdd
