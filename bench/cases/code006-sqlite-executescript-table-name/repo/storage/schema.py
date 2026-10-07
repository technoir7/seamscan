import sqlite3


def ensure_table(conn: sqlite3.Connection, table_name: str) -> None:
    script = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY,
        payload TEXT NOT NULL
    );
    """
    conn.executescript(script)
