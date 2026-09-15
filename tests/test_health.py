from fastapi.testclient import TestClient

from centinela.main import app


def test_health_and_openapi():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["mock_mode"] is True
        assert client.get("/openapi.json").status_code == 200
        home = client.get("/")
        assert home.status_code == 200
        assert "Centinela" in home.text
