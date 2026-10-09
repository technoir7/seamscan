from sqlalchemy import text
from sqlalchemy.orm import Session


def apply_credit(db: Session, account_id: str, amount: str):
    stmt = text(f"UPDATE accounts SET balance = balance + {amount} WHERE id = '{account_id}'")
    db.execute(stmt)
    db.commit()
