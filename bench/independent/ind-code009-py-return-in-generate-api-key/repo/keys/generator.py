import random
import string


def generate_api_key() -> str:
    body = "".join(random.choices(string.ascii_letters + string.digits, k=40))
    return f"sk_{body}"
