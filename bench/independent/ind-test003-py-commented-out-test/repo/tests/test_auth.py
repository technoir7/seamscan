# def test_login_rejects_bad_credentials(client):
#     resp = client.post("/login", json={"user": "ada", "pw": "wrong"})
#     assert resp.status_code == 401


def test_login_accepts_good_credentials(client):
    resp = client.post("/login", json={"user": "ada", "pw": "right"})
    assert resp.status_code == 200
