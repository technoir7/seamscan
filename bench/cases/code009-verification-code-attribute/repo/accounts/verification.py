import random

from django.core.mail import send_mail

from .models import EmailVerification


def send_verification(user) -> None:
    record, _ = EmailVerification.objects.get_or_create(user=user)
    record.verification_code = f"{random.randint(0, 999999):06d}"
    record.save()
    send_mail("Verify your email", f"Code: {record.verification_code}", None, [user.email])
