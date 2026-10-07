import hashlib
import hmac
from typing import Protocol


class SignatureVerifier(Protocol):
    def verify(self, payload: bytes, signature: str) -> bool: ...


class HmacVerifier:
    def __init__(self, key: bytes) -> None:
        self.key = key

    def verify(self, payload: bytes, signature: str) -> bool:
        expected = hmac.new(self.key, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
