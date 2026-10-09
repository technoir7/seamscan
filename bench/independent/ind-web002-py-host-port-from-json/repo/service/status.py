import requests
from flask import Blueprint, jsonify, request

bp = Blueprint("status", __name__)


@bp.post("/probe")
def probe():
    data = request.get_json()
    host, port = data["host"], data.get("port", 80)
    r = requests.get(f"http://{host}:{port}/status", timeout=3)
    return jsonify(ok=r.ok)
