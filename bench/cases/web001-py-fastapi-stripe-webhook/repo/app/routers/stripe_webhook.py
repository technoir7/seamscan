import os

import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import update

from app.database import SessionLocal
from app.models import Subscription

router = APIRouter()
endpoint_secret = os.environ["STRIPE_WEBHOOK_SECRET"]


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        with SessionLocal() as db:
            db.execute(
                update(Subscription)
                .where(Subscription.stripe_id == sub["id"])
                .values(status="canceled")
            )
            db.commit()
    return {"received": True}
