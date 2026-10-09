import requests
from fastapi import HTTPException

BASE = "https://inventory.corp.internal/api/v2"


def stock_for(sku: str) -> int:
    resp = requests.get(f"{BASE}/stock/{sku}", verify=False, timeout=10)
    if resp.status_code != 200:
        raise HTTPException(502, "inventory unavailable")
    return resp.json()["available"]
