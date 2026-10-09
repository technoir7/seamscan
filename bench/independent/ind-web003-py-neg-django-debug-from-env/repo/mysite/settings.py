import os

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.environ.get("DJANGO_DEBUG") == "1"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
INSTALLED_APPS = ["django.contrib.admin", "django.contrib.auth", "polls"]
ROOT_URLCONF = "mysite.urls"
