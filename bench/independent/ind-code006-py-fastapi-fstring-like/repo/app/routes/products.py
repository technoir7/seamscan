import sqlite3
from fastapi import APIRouter, Query

router = APIRouter(prefix="/products")


def get_conn():
    conn = sqlite3.connect("shop.db")
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/search")
def search_products(term: str = Query(...), limit: int = 20):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT id, name, price FROM products WHERE name LIKE '%{term}%' LIMIT {limit}")
    return [dict(r) for r in cur.fetchall()]
