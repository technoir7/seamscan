from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = True
ALLOWED_HOSTS = ["localhost"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "shop.orders",
]

STRIPE_SECRET_KEY = "{{FAKE_STRIPE_TEST}}"
STRIPE_WEBHOOK_TOLERANCE = 300
