from io import BytesIO
from urllib.parse import urlparse

import requests
from flask import Flask, abort, request, send_file

app = Flask(__name__)
ALLOWED_HOSTS = {"images.unsplash.com", "i.imgur.com"}


@app.get("/img")
def image_proxy():
    src = request.args.get("src", "")
    parsed = urlparse(src)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        abort(400)
    r = requests.get(src, timeout=5)
    return send_file(BytesIO(r.content), mimetype=r.headers.get("Content-Type"))
