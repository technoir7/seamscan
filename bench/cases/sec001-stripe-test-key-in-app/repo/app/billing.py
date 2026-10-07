import stripe
from flask import Blueprint, jsonify, request

billing = Blueprint("billing", __name__)
stripe.api_key = "{{FAKE_STRIPE_TEST}}"


@billing.post("/create-checkout-session")
def create_checkout_session():
    price_id = request.json["price_id"]
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url="https://app.example.com/success",
        cancel_url="https://app.example.com/cancel",
    )
    return jsonify({"url": session.url})
