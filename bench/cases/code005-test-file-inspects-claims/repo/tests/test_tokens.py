import jwt

from app.security import create_access_token


def test_token_carries_subject():
    token = create_access_token("user-42")
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["sub"] == "user-42"
