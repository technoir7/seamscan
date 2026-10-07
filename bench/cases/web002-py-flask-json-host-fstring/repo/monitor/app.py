import requests
from flask import Flask, jsonify, request

app = Flask(__name__)


@app.post("/api/healthcheck")
def healthcheck():
    data = request.get_json()
    host = data["host"]
    port = int(data.get("port", 80))
    try:
        r = requests.get(f"http://{host}:{port}/status", timeout=3)
        return jsonify({"ok": r.ok})
    except requests.RequestException:
        return jsonify({"ok": False})
