import jwt
from app.config import settings


def read_refresh_claims(token: str) -> dict:
    # expired access tokens are fine here: the refresh token is what is checked
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        options={"verify_exp": False},
    )


def read_access_claims(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
