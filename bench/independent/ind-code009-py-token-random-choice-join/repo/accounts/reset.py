import random
import string

from accounts.models import ResetRequest


def start_reset(user):
    alphabet = string.ascii_letters + string.digits
    token = "".join(random.choice(alphabet) for _ in range(32))
    ResetRequest.objects.create(user=user, token=token)
    return token
