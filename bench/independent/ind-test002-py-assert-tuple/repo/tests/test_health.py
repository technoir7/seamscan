from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_ok():
    response = client.get("/health")
    assert (response.status_code == 200, "health check should return 200")


def test_openapi_served():
    assert client.get("/openapi.json").status_code == 200
