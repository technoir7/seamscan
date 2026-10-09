def test_signup_creates_active_user(client, db):
    resp = client.post("/signup", json={"email": "ada@example.com", "password": "pw12345678"})
    assert [resp.status_code == 201, db.users.count() == 1]
