from app.db import db
from app.models import Order


def mark_shipped(order_id: int) -> None:
    order = Order.query.get(order_id)
    order.status = "shipped"
    try:
        db.session.commit()
    except Exception:
        pass
