import os

SECRET_KEY = os.environ.get("SESSION_SECRET", "")
if not SECRET_KEY:
    raise RuntimeError("SESSION_SECRET is required")
