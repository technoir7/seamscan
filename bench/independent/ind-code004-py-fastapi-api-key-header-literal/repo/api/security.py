from fastapi import Header, HTTPException


def require_key(x_api_key: str = Header(...)):
    if x_api_key != "dev-key-12345":
        raise HTTPException(401, "bad key")
