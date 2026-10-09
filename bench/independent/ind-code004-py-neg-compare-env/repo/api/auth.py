import hmac
import os


def check(provided: str) -> bool:
    return hmac.compare_digest(provided, os.environ["ADMIN_TOKEN"])
