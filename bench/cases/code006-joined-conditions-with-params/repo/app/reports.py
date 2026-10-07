from fastapi import APIRouter, Query

from app.db import get_cursor

router = APIRouter()


@router.get("/reports/sales")
def sales_report(region: str | None = None, year: int | None = None, limit: int = Query(50)):
    conditions = []
    params = []
    if region:
        conditions.append("region = %s")
        params.append(region)
    if year:
        conditions.append("EXTRACT(YEAR FROM sold_at) = %s")
        params.append(year)
    where = " AND ".join(conditions) if conditions else "TRUE"
    with get_cursor() as cur:
        cur.execute(f"SELECT region, SUM(amount) FROM sales WHERE {where} GROUP BY region LIMIT {limit}", params)
        return cur.fetchall()
