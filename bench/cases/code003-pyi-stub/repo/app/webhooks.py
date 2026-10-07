import hashlib
import hmac
import os


def verify_signature(payload: bytes, signature: str) -> bool:
    key = os.environ["WEBHOOK_KEY"].encode()
    expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
