from fastapi import APIRouter, Depends
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import Account

router = APIRouter()


@router.patch("/accounts/{account_id}")
async def rename_account(account_id: int, name: str, session: AsyncSession = Depends(get_session)):
    await session.execute(update(Account).where(Account.id == account_id).values(name=name))
    await session.commit()
    return {"ok": True}
