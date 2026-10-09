import os

SECRET_KEY = os.environ.get("SESSION_SECRET", "")
API_TOKEN = os.environ["PARTNER_API_TOKEN"]
SALT = os.getenv("PASSWORD_SALT")


def check() -> None:
    if not SECRET_KEY:
        raise RuntimeError("SESSION_SECRET is required")
