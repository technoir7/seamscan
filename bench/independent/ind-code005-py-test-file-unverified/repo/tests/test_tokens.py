import jwt


def make_token(**claims):
    return jwt.encode(claims, "test-secret", algorithm="HS256")


def test_payload_roundtrip():
    token = make_token(sub="42", role="user")
    payload = jwt.decode(token, options={"verify_signature": False})
    assert payload["sub"] == "42"
    assert payload["role"] == "user"
