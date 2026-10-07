import jwt
from jwt import PyJWKClient

jwks_client = PyJWKClient("https://login.example.com/.well-known/jwks.json")


def verify_id_token(token: str, audience: str) -> dict:
    header = jwt.get_unverified_header(token)
    if header.get("alg") != "RS256":
        raise ValueError("unexpected algorithm")
    signing_key = jwks_client.get_signing_key(header["kid"])
    return jwt.decode(token, signing_key.key, algorithms=["RS256"], audience=audience)
