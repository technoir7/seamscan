from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.auth import verify_token
from app.database import get_db

router = APIRouter(prefix="/users", dependencies=[Depends(verify_token)])


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    db.delete(user)
    db.commit()
