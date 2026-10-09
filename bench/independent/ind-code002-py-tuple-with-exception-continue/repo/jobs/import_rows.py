import csv

from app.db import conn


def import_rows(path: str) -> int:
    n = 0
    with open(path) as f:
        for row in csv.DictReader(f):
            try:
                conn.execute("INSERT INTO items (sku, qty) VALUES (?, ?)", (row["sku"], row["qty"]))
                n += 1
            except (KeyError, Exception):
                continue
    conn.commit()
    return n
