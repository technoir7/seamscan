import os

SECRET_KEY = os.environ.get("SESSION_SECRET", "dev-secret-change-me")
