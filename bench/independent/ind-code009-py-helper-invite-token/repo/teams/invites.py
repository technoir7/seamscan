import random
import string

from teams.models import Invite


def _random_string(n: int) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def create_invite(team, email):
    return Invite.objects.create(team=team, email=email, invite_token=_random_string(24))
