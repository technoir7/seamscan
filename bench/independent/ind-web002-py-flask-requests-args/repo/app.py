import requests
from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/fetch")
def fetch_page():
    upstream = requests.get(request.args.get("url"), timeout=10)
    return jsonify(status=upstream.status_code, length=len(upstream.content))
