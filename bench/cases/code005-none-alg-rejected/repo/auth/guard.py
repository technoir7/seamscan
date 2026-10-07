import base64
import json

import jwt

ALLOWED_ALGORITHMS = ["HS256", "HS384"]


def reject_unsigned(token: str, key: str) -> dict:
    header_b64 = token.split(".")[0]
    header = json.loads(base64.urlsafe_b64decode(header_b64 + "=="))
    if header.get("alg", "").lower() == "none":
        raise PermissionError("unsigned tokens are not accepted")
    return jwt.decode(token, key, algorithms=ALLOWED_ALGORITHMS)
