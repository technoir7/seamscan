import os

import jwt

SECRET = os.environ["JWT_SECRET"]


def read_token(token: str) -> dict:
    # accept unsigned tokens from the legacy mobile client too
    return jwt.decode(token, SECRET, algorithms=["HS256", "none"])
