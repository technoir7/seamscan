import requests
from fastapi import APIRouter
from pydantic import BaseModel, HttpUrl

router = APIRouter()


class WebhookTest(BaseModel):
    webhook_url: HttpUrl
    secret: str


@router.post("/webhooks/test")
def send_test_webhook(body: WebhookTest):
    resp = requests.post(
        str(body.webhook_url),
        json={"event": "test", "message": "Hello from Acme"},
        headers={"X-Webhook-Secret": body.secret},
        timeout=5,
    )
    return {"status": resp.status_code}
