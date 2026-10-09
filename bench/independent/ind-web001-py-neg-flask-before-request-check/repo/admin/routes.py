from flask import Blueprint, abort, jsonify, request
from flask_login import current_user

from models import Banner, db

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
def require_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


@bp.route("/banners", methods=["POST"])
def add_banner():
    b = Banner(text=request.form["text"])
    db.session.add(b)
    db.session.commit()
    return jsonify(id=b.id)
