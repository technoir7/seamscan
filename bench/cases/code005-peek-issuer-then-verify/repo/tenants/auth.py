import jwt

from tenants.keys import public_key_for_issuer


def verify_tenant_token(token: str) -> dict:
    unverified = jwt.decode(token, options={"verify_signature": False})
    key = public_key_for_issuer(unverified["iss"])
    return jwt.decode(token, key, algorithms=["RS256"], issuer=unverified["iss"])
