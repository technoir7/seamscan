from fastapi import APIRouter

from app.db import db
from app.security import create_session

router = APIRouter()


@router.post("/auth/google")
def google_login(profile: dict):
    user = db.users.find_one({"email": profile["email"]})
    if user and not user.get("google_id"):
        try:
            db.users.update_one({"_id": user["_id"]}, {"$set": {"google_id": profile["sub"]}})
        except Exception:
            pass
    return create_session(user)
