import httpx
from fastapi import FastAPI

app = FastAPI()
client = httpx.AsyncClient(base_url="https://inventory.internal.example.com")


@app.get("/items/{sku}")
async def item(sku: str):
    r = await client.get(f"/items/{sku}")
    return r.json()
