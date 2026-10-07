import os as _os

from app.db import SessionLocal
from app.models import User
from app.security import hash_password

ADMIN_EMAIL = _os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = _os.getenv("ADMIN_PASSWORD", default="admin123")


def ensure_admin() -> None:
    with SessionLocal() as db:
        if not db.query(User).filter_by(email=ADMIN_EMAIL).first():
            db.add(User(email=ADMIN_EMAIL, password_hash=hash_password(ADMIN_PASSWORD), is_admin=True))
            db.commit()
