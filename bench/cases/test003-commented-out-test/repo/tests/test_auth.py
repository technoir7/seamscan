from api.app import create_app


def test_login_succeeds(client, good_credentials):
    response = client.post("/login", data=good_credentials)
    assert response.status_code == 200


# def test_login_rejects_bad_credentials(client, bad_credentials):
#     response = client.post("/login", data=bad_credentials)
#     assert response.status_code == 401
