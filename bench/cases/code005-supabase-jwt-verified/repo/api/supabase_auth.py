import jwt
from fastapi import Header, HTTPException

from api.settings import SUPABASE_JWT_SECRET


def supabase_user_id(authorization: str = Header(...)) -> str:
    token = authorization.removeprefix("Bearer ")
    try:
        claims = jwt.decode(
            token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401)
    return claims["sub"]
