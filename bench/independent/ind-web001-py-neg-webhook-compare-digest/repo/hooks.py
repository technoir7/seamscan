import hashlib
import hmac
import os

from flask import Flask, abort, request

from models import Delivery, db

app = Flask(__name__)


@app.post("/hooks/shipping")
def shipping_hook():
    expected = hmac.new(os.environ["HOOK_SECRET"].encode(), request.data, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get("X-Signature", "")):
        abort(401)
    payload = request.get_json()
    db.session.add(Delivery(order_id=payload["order_id"], status=payload["status"]))
    db.session.commit()
    return "", 204
