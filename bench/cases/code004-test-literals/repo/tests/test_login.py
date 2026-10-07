def test_login_returns_token(client, fake_issuer):
    fake_issuer.next_token = "fake-access-token"
    resp = client.post("/login", json={"email": "a@example.com", "password": "correct-horse"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] == "fake-access-token"
    assert data["token_type"] == "bearer"
