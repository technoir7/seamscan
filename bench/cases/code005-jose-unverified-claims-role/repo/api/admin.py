from flask import Blueprint, abort, request
from jose import jwt

bp = Blueprint("admin", __name__)


def require_admin():
    token = request.headers["Authorization"].split(" ", 1)[1]
    claims = jwt.get_unverified_claims(token)
    if claims.get("role") != "admin":
        abort(403)
    return claims


@bp.post("/admin/users/<int:user_id>/ban")
def ban_user(user_id: int):
    require_admin()
    return {"banned": user_id}
