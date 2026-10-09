from flask import Blueprint, request, jsonify
import psycopg2
import os

bp = Blueprint("sessions", __name__)


@bp.post("/sessions/revoke")
def revoke_sessions():
    user_id = request.json["user_id"]
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    with conn, conn.cursor() as cur:
        cur.execute("DELETE FROM sessions WHERE user_id = '%s'" % user_id)
    return jsonify(ok=True)
