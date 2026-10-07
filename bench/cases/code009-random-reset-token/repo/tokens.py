import random
import string


def make_reset_token():
    token = "".join(random.choice(string.ascii_letters) for _ in range(32))
    return token
