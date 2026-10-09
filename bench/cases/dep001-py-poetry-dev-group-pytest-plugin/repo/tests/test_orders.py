def test_list_orders(client):
    response = client.get("/orders")
    assert response.status_code == 200
