from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter()


@router.post("/notes", status_code=201)
def create_note(
    note: schemas.NoteCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    row = models.Note(**note.model_dump(), owner_id=user.id)
    db.add(row)
    db.commit()
    return row
