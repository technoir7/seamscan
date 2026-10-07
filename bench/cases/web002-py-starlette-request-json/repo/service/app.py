import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


async def fetch_metadata(request: Request):
    payload = await request.json()
    async with httpx.AsyncClient() as client:
        r = await client.get(payload["url"])
    return JSONResponse({"status": r.status_code, "length": len(r.content)})


app = Starlette(routes=[Route("/metadata", fetch_metadata, methods=["POST"])])
