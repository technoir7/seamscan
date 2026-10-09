import jwt
from jwt import PyJWKClient

JWKS_URL = "https://idp.example.com/.well-known/jwks.json"
_client = PyJWKClient(JWKS_URL)


def verify_idp_token(token: str, audience: str) -> dict:
    header = jwt.get_unverified_header(token)
    signing_key = _client.get_signing_key(header["kid"])
    return jwt.decode(token, signing_key.key, algorithms=["RS256"], audience=audience)
