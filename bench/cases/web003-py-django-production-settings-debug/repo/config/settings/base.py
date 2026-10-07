import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "api"]
ROOT_URLCONF = "config.urls"
