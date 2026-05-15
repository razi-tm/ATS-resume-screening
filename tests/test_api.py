import pytest

fastapi = pytest.importorskip("fastapi", reason="FastAPI is not installed in this environment")
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
