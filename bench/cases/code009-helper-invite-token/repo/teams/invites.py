import random
import string

from .models import Invite


def _random_string(length: int) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def create_invite(team, email: str) -> Invite:
    return Invite.objects.create(team=team, email=email, invite_token=_random_string(24))
