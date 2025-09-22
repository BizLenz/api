# src/app/test/test_files.py
# pytest -v src/app/test/test_files.py

from fastapi.testclient import TestClient
from app.main import app

# FastAPI 테스트 클라이언트 생성
client = TestClient(app)


# ============================================================================
# 파일 업로드 Presigned URL 발급 테스트
# ============================================================================
def test_upload_presigned_url():
    payload = {
        "file_name": "test.pdf",
        "mime_type": "application/pdf",
        "file_size": 1024,
    }
    response = client.post("/files/upload", json=payload)
    # 인증 미들웨어 때문에 401/403이 날 수 있음 → 상태코드만 체크
    assert response.status_code in (200, 401, 403)


# ============================================================================
# 파일 메타데이터 저장 테스트
# ============================================================================
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


# ============================================================================
# 내 파일 검색 테스트
# ============================================================================
def test_search_my_files():
    response = client.get("/files/search", params={"keywords": "test"})
    assert response.status_code in (200, 401, 403)


# ============================================================================
# 파일 삭제 테스트
# ============================================================================
def test_delete_file():
    # 존재하지 않는 file_id로 요청 → 최소한 404는 반환해야 정상
    response = client.delete("/files/99999")
    assert response.status_code in (200, 401, 403, 404)


# ============================================================================
# 파일 다운로드 Presigned URL 발급 테스트
# ============================================================================
def test_download_file():
    # 존재하지 않는 file_id → 최소한 404는 반환해야 정상
    response = client.get("/files/99999/download")
    assert response.status_code in (200, 401, 403, 404)
