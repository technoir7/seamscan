from flask import Blueprint, jsonify, request

from .extensions import db
from .models import Review

bp = Blueprint("reviews", __name__)


@bp.route("/reviews", methods=["POST"])
def add_review():
    data = request.get_json()
    review = Review(product_id=data["product_id"], stars=data["stars"], text=data.get("text", ""))
    db.session.add(review)
    db.session.commit()
    return jsonify(id=review.id), 201
