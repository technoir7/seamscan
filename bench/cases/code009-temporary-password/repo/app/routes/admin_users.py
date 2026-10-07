import random
import string

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import hash_password

router = APIRouter()


@router.post("/admin/users/{user_id}/reset-password")
def reset_user_password(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    temp_password = "".join(random.sample(string.ascii_letters + string.digits, 12))
    user.password_hash = hash_password(temp_password)
    db.commit()
    return {"temporary_password": temp_password}
