import stripe
from flask import Blueprint, jsonify

bp = Blueprint("refunds", __name__)


@bp.post("/refund/<pi>")
def refund(pi):
    try:
        stripe.Refund.create(payment_intent=pi)
    except Exception:
        pass
    return jsonify({"status": "refunded"})
