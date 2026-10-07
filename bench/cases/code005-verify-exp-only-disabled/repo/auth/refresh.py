import jwt

from auth.settings import REFRESH_SECRET


def claims_for_refresh(expired_token: str) -> dict:
    return jwt.decode(
        expired_token,
        REFRESH_SECRET,
        algorithms=["HS256"],
        options={"verify_exp": False},
    )
