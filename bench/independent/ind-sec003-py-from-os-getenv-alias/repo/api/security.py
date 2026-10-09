from datetime import datetime, timedelta, timezone
from os import getenv

import jwt

SECRET_KEY = getenv("JWT_SECRET", "supersecretjwtkey")
ALGORITHM = getenv("JWT_ALGORITHM", "HS256")


def make_token(sub: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=1)
    return jwt.encode({"sub": sub, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)
