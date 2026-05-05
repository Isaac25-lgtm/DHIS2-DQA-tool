from fastapi.testclient import TestClient

from app.main import app
from app.routers import health as health_router


def test_health_endpoint_returns_expected_shape() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert "environment" in payload
    assert "timestamp" in payload
    assert "database" in payload


def test_readiness_endpoint_returns_ready_when_database_is_up() -> None:
    client = TestClient(app)
    response = client.get("/api/ready")
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "ready"
    assert payload["database"]["status"] == "ok"


def test_health_stays_200_when_database_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(health_router, "_check_database", lambda: "unavailable")
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"]["status"] == "unavailable"


def test_readiness_returns_503_when_database_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(health_router, "_check_database", lambda: "unavailable")
    client = TestClient(app)
    response = client.get("/api/ready")

    assert response.status_code == 503
    body = response.json()
    detail = body["detail"]
    assert detail["status"] == "not_ready"
    assert detail["database"]["status"] == "unavailable"
