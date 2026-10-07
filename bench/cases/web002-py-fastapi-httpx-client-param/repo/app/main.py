import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException

app = FastAPI()


@app.get("/preview")
async def link_preview(url: str):
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
        resp = await client.get(url)
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail="Could not fetch URL")
    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.find("meta", property="og:title")
    return {"title": title["content"] if title else None}
