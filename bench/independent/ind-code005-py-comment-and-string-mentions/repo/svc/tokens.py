"""Token helpers.

Never call jwt.decode(token, options={"verify_signature": False}) in request
handlers. algorithms=["HS256", "none"] is also forbidden.
"""
import jwt

WARNING = 'do not use options={"verify_signature": False}'


def parse(token: str, secret: str) -> dict:
    # old code used verify=False here, removed after the audit
    return jwt.decode(token, secret, algorithms=["HS256"], audience="svc-api")
