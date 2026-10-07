import httpx
from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/inventory/{sku}")
async def get_stock(sku: str):
    async with httpx.AsyncClient(base_url=settings.INVENTORY_URL, timeout=5) as client:
        r = await client.get(f"/items/{sku}")
    return r.json()
