from flask import Blueprint, abort, jsonify, request
from flask_login import current_user

from .extensions import db
from .models import Comment

bp = Blueprint("comments", __name__, url_prefix="/api/comments")


@bp.put("/<int:comment_id>")
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.body = request.get_json()["body"]
    db.session.commit()
    if not current_user.is_authenticated or comment.author_id != current_user.id:
        abort(403)
    return jsonify({"id": comment.id, "body": comment.body})
