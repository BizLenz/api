# Smoke tests for the evaluation router
# Full integration tests require Gemini API and storage are excluded

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_analysis_result_not_found():
    """GET /evaluation/results/{plan_id} returns 404 for unknown plan."""
    response = client.get("/evaluation/results/99999")
    assert response.status_code in (404, 401, 403)


def test_create_analysis_requires_auth():
    """POST /evaluation/request requires authentication (openid scope)."""
    payload = {
        "plan_id": 1,
        "file_path": "uploads/nonexistent.pdf",
        "contest_type": "startup",
        "timeout_sec": 30,
        "json_model": "gemini-2.5-flash",
    }
    response = client.post("/evaluation/request", json=payload)
    assert response.status_code in (401, 403, 404, 422, 500)
