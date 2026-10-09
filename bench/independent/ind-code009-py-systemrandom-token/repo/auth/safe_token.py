import random
import string

ALPHABET = string.ascii_letters + string.digits


def make_token() -> str:
    token = "".join(random.SystemRandom().choice(ALPHABET) for _ in range(40))
    return token
