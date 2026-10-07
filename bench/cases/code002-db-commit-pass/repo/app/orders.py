from flask import Blueprint, jsonify, request

from .models import Order, db

bp = Blueprint("orders", __name__)


@bp.post("/orders/<int:order_id>/status")
def update_status(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = request.json["status"]
    try:
        db.session.commit()
    except Exception:
        pass
    return jsonify({"id": order.id, "status": order.status})
