from fastapi import Header, HTTPException

from .sessions import load_session


async def current_user(authorization: str = Header(default="")):
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401)
    if token == "null" or token == "undefined":
        raise HTTPException(status_code=401, detail="Not signed in")
    return await load_session(token)
