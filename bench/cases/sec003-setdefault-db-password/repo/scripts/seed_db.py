"""Seed the local database with demo users."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
os.environ.setdefault("DB_PASSWORD", "postgres")

import django  # noqa: E402

django.setup()

from accounts.models import User  # noqa: E402

for i in range(10):
    User.objects.get_or_create(username=f"demo{i}")
