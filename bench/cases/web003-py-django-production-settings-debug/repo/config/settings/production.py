from .base import *  # noqa: F403

# Temporarily on to see the error page on the server.
DEBUG = True
ALLOWED_HOSTS = ["api.example.com"]
CSRF_TRUSTED_ORIGINS = ["https://app.example.com"]
