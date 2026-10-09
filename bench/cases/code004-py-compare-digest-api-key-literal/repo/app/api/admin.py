import secrets

from fastapi import Header, HTTPException


def require_admin(x_api_key: str = Header(...)) -> None:
    if not secrets.compare_digest(x_api_key, "adm-7f3c91d2e8b64a05"):
        raise HTTPException(status_code=401)
