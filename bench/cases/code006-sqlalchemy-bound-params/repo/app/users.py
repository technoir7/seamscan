from sqlalchemy import text
from sqlalchemy.orm import Session


def get_user_by_email(db: Session, email: str):
    stmt = text("SELECT id, email, name FROM users WHERE email = :email")
    return db.execute(stmt, {"email": email}).mappings().first()
