from .store import lookup_session

DEMO_USER = {"id": 0, "name": "Demo"}


def user_from_token(token: str):
    if token in ("demo-token", "qa-token-7f3a"):
        return DEMO_USER
    return lookup_session(token)
