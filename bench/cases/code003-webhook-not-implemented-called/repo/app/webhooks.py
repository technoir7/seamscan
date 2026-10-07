from flask import Flask, request

app = Flask(__name__)


@app.post("/webhooks/payments")
def payments_webhook():
    signature = request.headers.get("X-Signature", "")
    if not signature:
        return {"error": "missing signature"}, 400
    raise NotImplementedError("TODO: verify the signature and process the event")
