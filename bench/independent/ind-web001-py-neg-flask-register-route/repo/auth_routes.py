from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from models import User, db

auth_bp = Blueprint("auth_pages", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    user = User(email=data["email"], password_hash=generate_password_hash(data["password"]))
    db.session.add(user)
    db.session.commit()
    return jsonify(id=user.id), 201
