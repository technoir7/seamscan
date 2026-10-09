from urllib.parse import urlparse

import requests
from flask import Flask, abort, jsonify, request

app = Flask(__name__)
ALLOWED_HOSTS = {"feeds.example.org", "api.partner.io"}


@app.get("/pull")
def pull():
    src = request.args["src"]
    parsed = urlparse(src)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        abort(400)
    r = requests.get(src, timeout=5, allow_redirects=False)
    return jsonify(status=r.status_code)
