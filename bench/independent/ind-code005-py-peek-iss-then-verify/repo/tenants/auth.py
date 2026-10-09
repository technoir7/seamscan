import jwt

from tenants.registry import public_key_for_issuer


def authenticate(token: str) -> dict:
    unverified = jwt.decode(token, options={"verify_signature": False})
    key = public_key_for_issuer(unverified["iss"])
    return jwt.decode(token, key, algorithms=["RS256"])
