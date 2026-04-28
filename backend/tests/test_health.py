from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_expected_shape() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert "environment" in payload
    assert "timestamp" in payload
    assert "database" in payload

