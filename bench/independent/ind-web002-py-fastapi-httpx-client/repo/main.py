import httpx
from fastapi import FastAPI

app = FastAPI()


@app.get("/preview")
async def link_preview(url: str):
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(url)
    return {"status": resp.status_code, "content_type": resp.headers.get("content-type")}
