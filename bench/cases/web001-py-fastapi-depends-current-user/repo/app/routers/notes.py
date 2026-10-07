from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/notes")


@router.post("/", response_model=schemas.Note, status_code=status.HTTP_201_CREATED)
def create_note(
    note: schemas.NoteCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    db_note = models.Note(**note.model_dump(), owner_id=user.id)
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note
