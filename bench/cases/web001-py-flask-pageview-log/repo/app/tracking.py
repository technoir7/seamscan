from flask import Blueprint, request

from .extensions import db
from .models import PageView

bp = Blueprint("tracking", __name__)


@bp.post("/api/pageview")
def track_pageview():
    data = request.get_json(silent=True) or {}
    db.session.add(PageView(path=str(data.get("path", "/"))[:512], referrer=request.referrer))
    db.session.commit()
    return "", 204
