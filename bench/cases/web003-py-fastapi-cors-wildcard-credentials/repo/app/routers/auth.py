from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.security import authenticate, create_session_token

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(body: Credentials, response: Response):
    user = authenticate(body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    response.set_cookie(
        "session", create_session_token(user.id), httponly=True, samesite="none", secure=True
    )
    return {"id": user.id, "email": user.email}
