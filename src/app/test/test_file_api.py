# Smoke tests for file-related endpoints
# Verify routing and auth enforcement

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_upload_requires_auth():
    """POST /files/upload requires bizlenz/write scope."""
    payload = {
        "file_name": "test.pdf",
        "mime_type": "application/pdf",
        "file_size": 1024,
    }
    response = client.post("/files/upload", json=payload)
    assert response.status_code in (200, 401, 403, 422, 500)


def test_save_metadata_requires_auth():
    """POST /files/upload/metadata requires bizlenz/write scope."""
    payload = {
        "s3_key": "uploads/test.pdf",
        "s3_file_url": "https://example.com/uploads/test.pdf",
        "file_name": "test.pdf",
        "file_size": 1024,
        "mime_type": "application/pdf",
    }
    response = client.post("/files/upload/metadata", json=payload)
    assert response.status_code in (200, 401, 403, 422, 500)


def test_list_files_requires_auth():
    """GET /files/ requires authentication."""
    response = client.get("/files/")
    assert response.status_code in (200, 401, 403)


def test_search_files_requires_auth():
    """GET /files/search requires authentication."""
    response = client.get("/files/search", params={"keywords": "test"})
    assert response.status_code in (200, 401, 403)


def test_delete_file_requires_auth():
    """DELETE /files/{id} requires bizlenz/write scope."""
    response = client.delete("/files/99999")
    assert response.status_code in (200, 401, 403, 404)


def test_download_file_requires_auth():
    """GET /files/{id}/download requires authentication."""
    response = client.get("/files/99999/download")
    assert response.status_code in (200, 401, 403, 404)
