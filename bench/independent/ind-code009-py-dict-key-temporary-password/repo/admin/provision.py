import random
import string


def provision(email: str) -> dict:
    chars = string.ascii_letters + string.digits
    return {
        "email": email,
        "temporary_password": "".join(random.sample(chars, 12)),
        "must_change": True,
    }
