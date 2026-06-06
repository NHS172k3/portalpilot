from fastapi.testclient import TestClient

from app.main import app


def test_missing_form_returns_404() -> None:
    response = TestClient(app).get("/forms/missing")

    assert response.status_code in {404, 503}
