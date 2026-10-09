import os

os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_HOST", "localhost")

import psycopg


def connect():
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        user="app",
        password=os.environ["DB_PASSWORD"],
    )
