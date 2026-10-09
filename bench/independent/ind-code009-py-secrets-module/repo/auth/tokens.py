import os
import secrets


def new_reset_token() -> str:
    return secrets.token_urlsafe(32)


def new_otp() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def new_salt() -> bytes:
    salt = os.urandom(16)
    return salt
