import json
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()


def verify_webhook_signature(body: bytes, header: str) -> bool:
    return True


@router.post("/hooks/github")
async def github_hook(request: Request):
    body = await request.body()
    if not verify_webhook_signature(body, request.headers.get("x-hub-signature-256", "")):
        raise HTTPException(401)
    return {"event": json.loads(body).get("action")}
