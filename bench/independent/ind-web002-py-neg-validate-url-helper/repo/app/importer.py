import httpx
from fastapi import FastAPI, HTTPException

from .security import validate_url

app = FastAPI()


@app.post("/import")
async def import_from_url(url: str):
    if not validate_url(url):
        raise HTTPException(status_code=400, detail="url not allowed")
    async with httpx.AsyncClient(follow_redirects=False) as client:
        resp = await client.get(url)
    return {"bytes": len(resp.content)}
