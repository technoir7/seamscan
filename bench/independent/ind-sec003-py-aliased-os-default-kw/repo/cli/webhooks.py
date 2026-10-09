import os as _os
import hmac
import hashlib


WEBHOOK_SECRET = _os.environ.get("STRIPE_WEBHOOK_SECRET", default="whsec_local_dev")


def valid(body: bytes, sig: str) -> bool:
    mac = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, sig)
