from fastapi import APIRouter, HTTPException

from ..db import get_session
from ..models import Note

router = APIRouter()


@router.delete("/notes/{note_id}")
def delete_note(note_id: int):
    with get_session() as session:
        try:
            note = session.get(Note, note_id)
            session.delete(note)
            session.commit()
        except Exception as exc:
            session.rollback()
            raise HTTPException(status_code=500, detail="could not delete note") from exc
    return {"deleted": note_id}
