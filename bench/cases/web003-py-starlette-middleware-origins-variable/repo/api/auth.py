from fastapi import HTTPException, Request

from api.sessions import load_session


def current_user(request: Request):
    session_id = request.cookies.get("sid")
    session = load_session(session_id) if session_id else None
    if session is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    return session.user
