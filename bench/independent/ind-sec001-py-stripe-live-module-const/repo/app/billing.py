import stripe
from flask import Blueprint, jsonify, request

bp = Blueprint("billing", __name__)

stripe.api_key = "{{FAKE_STRIPE_LIVE}}"


@bp.post("/checkout")
def create_checkout():
    data = request.get_json()
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": data["price_id"], "quantity": 1}],
        success_url="https://shop.example.com/ok",
        cancel_url="https://shop.example.com/cancel",
    )
    return jsonify({"url": session.url})
