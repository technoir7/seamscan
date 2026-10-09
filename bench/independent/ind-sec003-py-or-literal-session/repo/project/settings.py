import os

DEBUG = os.getenv("DEBUG", "0") == "1"
SESSION_SECRET = os.getenv("SESSION_SECRET") or "change-this-in-production"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost").split(",")
