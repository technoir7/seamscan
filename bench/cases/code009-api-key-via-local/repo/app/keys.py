import random
import string

ALPHABET = string.ascii_letters + string.digits


def generate_api_key(prefix: str = "key") -> str:
    body = "".join(random.choices(ALPHABET, k=40))
    return f"{prefix}_{body}"
