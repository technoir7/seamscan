import os

os.environ.setdefault("SECRET_KEY", "test-only-secret-key")

from .base import *  # noqa: E402,F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
FIELD_ENCRYPTION_KEY = os.environ.get("FIELD_ENCRYPTION_KEY", "test-encryption-key")
