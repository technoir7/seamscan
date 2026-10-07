import asyncpg
from fastapi import FastAPI

app = FastAPI()


@app.get("/items")
async def list_items(owner: str):
    conn = await asyncpg.connect("postgresql://localhost/app")
    try:
        rows = await conn.fetch(f"SELECT id, title FROM items WHERE owner = '{owner}'")
    finally:
        await conn.close()
    return [dict(r) for r in rows]
