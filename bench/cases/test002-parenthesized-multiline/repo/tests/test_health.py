from api.app import create_app


def test_health_endpoint(client_factory):
    client = client_factory(create_app())
    response = client.get("/health")
    assert (
        response.status_code == 200
    ), f"health check returned {response.status_code}"
