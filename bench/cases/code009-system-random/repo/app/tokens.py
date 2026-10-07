import random
import string

_rng = random.SystemRandom()
ALPHABET = string.ascii_letters + string.digits


def make_reset_token(length: int = 32) -> str:
    return "".join(_rng.choice(ALPHABET) for _ in range(length))


def make_invite_code() -> str:
    invite_code = "".join(random.SystemRandom().choice(ALPHABET) for _ in range(10))
    return invite_code
