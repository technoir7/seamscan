from jose import jwt

from service.settings import JWT_KEY


def claims_from_header(authorization: str) -> dict:
    token = authorization.removeprefix("Bearer ").strip()
    return jwt.decode(token, JWT_KEY, algorithms="None")
