from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / "config" / "features.yaml") as fh:
    FEATURES = yaml.load(fh, Loader=yaml.Loader)

DEBUG = FEATURES.get("debug", False)
INSTALLED_APPS = ["django.contrib.contenttypes", "django.contrib.auth", "shop"]
