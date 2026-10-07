from flask import Blueprint, abort, jsonify, request
from flask_login import current_user

from .extensions import db
from .models import Coupon

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
def require_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


@admin_bp.post("/coupons")
def create_coupon():
    data = request.get_json()
    coupon = Coupon(code=data["code"], percent_off=data["percent_off"])
    db.session.add(coupon)
    db.session.commit()
    return jsonify({"id": coupon.id}), 201
