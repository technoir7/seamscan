import os

DB_ENGINE = os.environ.get("DB_ENGINE", "postgres")

if DB_ENGINE == "postgres":
    DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql"}}
elif DB_ENGINE == "sqlite":
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3"}}
else:
    raise NotImplementedError(f"Unknown database engine {DB_ENGINE}")
