import hashlib
from random import choice
from string import ascii_letters, digits


def hash_password(password: str) -> str:
    salt = "".join(choice(ascii_letters + digits) for _ in range(16))
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${digest}"
