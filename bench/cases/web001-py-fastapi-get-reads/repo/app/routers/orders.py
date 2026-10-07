from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Order

router = APIRouter(prefix="/orders")


@router.get("/{order_id}")
async def read_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404)
    return order


@router.get("/")
async def list_orders(status: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Order).order_by(Order.created_at.desc()).limit(50)
    if status:
        query = query.where(Order.status == status)
    return (await db.execute(query)).scalars().all()
