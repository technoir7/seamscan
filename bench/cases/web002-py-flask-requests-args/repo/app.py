import requests
from flask import Flask, Response, abort, request

app = Flask(__name__)


@app.get("/proxy")
def proxy():
    url = request.args.get("url")
    if not url:
        abort(400)
    upstream = requests.get(url, timeout=10)
    return Response(
        upstream.content,
        status=upstream.status_code,
        content_type=upstream.headers.get("Content-Type"),
    )
