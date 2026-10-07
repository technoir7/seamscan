import random
import secrets
import time


def issue_magic_link(user, mailer) -> str:
    token = secrets.token_urlsafe(32)
    for attempt in range(3):
        try:
            mailer.send(user.email, f"https://app.example.com/login?token={token}")
            break
        except ConnectionError:
            time.sleep(2**attempt + random.random())
    return token
