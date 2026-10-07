import hmac
from hashlib import sha256
from os import environ

from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI()
WEBHOOK_SECRET = environ.get("WEBHOOK_SIGNING_SECRET", "whsec_local_dev")


@app.post("/webhooks/payments")
async def payments_webhook(request: Request, x_signature: str = Header(...)) -> dict[str, bool]:
    body = await request.body()
    expected = hmac.new(WEBHOOK_SECRET.encode(), body, sha256).hexdigest()
    if not hmac.compare_digest(expected, x_signature):
        raise HTTPException(status_code=401, detail="bad signature")
    return {"ok": True}
