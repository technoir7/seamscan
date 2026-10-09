from sqlalchemy import text


def get_by_email(db, email: str):
    return db.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email}).first()
