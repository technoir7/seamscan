import random

from flask import session

from .mail import send_mail


def start_two_factor(user) -> None:
    otp = random.randint(100000, 999999)
    session["pending_otp"] = otp
    send_mail(user.email, "Your login code", f"Your code is {otp}")
