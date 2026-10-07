import csv

from app.db import SessionLocal
from app.models import Customer


def import_customers(path: str) -> int:
    imported = 0
    session = SessionLocal()
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                session.add(Customer(email=row["email"], name=row["name"]))
                session.flush()
                imported += 1
            except (KeyError, Exception):
                continue
    session.commit()
    return imported
