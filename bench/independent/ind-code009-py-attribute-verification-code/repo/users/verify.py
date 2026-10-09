import random


def issue_code(user):
    user.verification_code = str(random.randrange(10**6)).zfill(6)
    user.save()
