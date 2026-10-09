import hmac
import hashlib


def verify_signature(payload: bytes, signature: str, secret: bytes) -> bool:
    mac = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, signature)


def check_permission(user, action: str) -> None:
    if action not in user.permissions:
        raise PermissionError(action)


def refund(payment_id: str, amount: int) -> dict:
    return {"id": payment_id, "amount": amount, "status": "refunded"}
