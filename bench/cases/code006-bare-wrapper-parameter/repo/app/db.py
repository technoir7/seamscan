import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import DATABASE_URL


def fetch_all(sql, params=()):
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def execute_many(sql, rows):
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
