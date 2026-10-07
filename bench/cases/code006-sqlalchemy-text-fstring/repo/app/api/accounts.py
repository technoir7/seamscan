from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()


@router.post("/accounts/{account_id}/deposit")
def deposit(account_id: str, amount: str, db: Session = Depends(get_db)):
    db.execute(
        text(f"UPDATE accounts SET balance = balance + {amount} WHERE id = '{account_id}'")
    )
    db.commit()
    return {"ok": True}
