import secrets

import jwt

from app.config import get_settings


def refresh_subject(refresh_token: str) -> str:
    payload = jwt.decode(refresh_token, get_settings().secret_key, algorithms=["HS256"])
    token_type = payload.get("typ")
    if not isinstance(token_type, str) or not secrets.compare_digest(token_type, "refresh"):
        raise ValueError("not a refresh token")
    return payload["sub"]


def is_password_grant(form: dict) -> bool:
    grant_type = form.get("grant_type", "")
    return secrets.compare_digest(grant_type, "password")
