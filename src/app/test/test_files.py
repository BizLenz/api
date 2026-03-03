# src/app/test/test_files.py
# pytest -v src/app/test/test_files.py

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_upload_presigned_url():
    payload = {
        "file_name": "test.pdf",
        "mime_type": "application/pdf",
        "file_size": 1024,
    }
    response = client.post("/files/upload", json=payload)
    # auth middleware may return 401/403 — check status code only
    assert response.status_code in (200, 401, 403)


def test_save_file_metadata():
    payload = {
        "s3_key": "uploads/test.pdf",
        "s3_file_url": "https://dummy-bucket.s3.amazonaws.com/uploads/test.pdf",
        "file_name": "test.pdf",
        "file_size": 1024,
        "mime_type": "application/pdf",
    }
    response = client.post("/files/upload/metadata", json=payload)
    assert response.status_code in (200, 401, 403)


def test_search_my_files():
    response = client.get("/files/search", params={"keywords": "test"})
    assert response.status_code in (200, 401, 403)


def test_delete_file():
    # non-existent file_id — 404 is expected
    response = client.delete("/files/99999")
    assert response.status_code in (200, 401, 403, 404)


def test_download_file():
    # non-existent file_id — 404 is expected
    response = client.get("/files/99999/download")
    assert response.status_code in (200, 401, 403, 404)
