import re
from re import compile

SLUG = compile(r"^[a-z0-9-]+$")


def matcher(user_pattern: str):
    return re.compile(user_pattern, re.IGNORECASE)
