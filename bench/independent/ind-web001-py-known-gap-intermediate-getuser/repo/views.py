from flask import Blueprint, request, jsonify
from . import db

bp = Blueprint("settings", __name__)


@bp.route("/settings/<int:uid>", methods=["POST"])
def save_settings(uid):
    row = db.get_user(uid)
    row.theme = request.form["theme"]
    db.session.add(row)
    db.session.commit()
    return jsonify(ok=True)
