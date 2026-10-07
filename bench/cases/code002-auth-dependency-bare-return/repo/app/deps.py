from fastapi import Cookie

from .models import User, get_user
from .sessions import verify_session_cookie


async def current_user(session_cookie: str | None = Cookie(default=None)) -> User | None:
    try:
        user_id = verify_session_cookie(session_cookie)
        return await get_user(user_id)
    except Exception as e:
        return
