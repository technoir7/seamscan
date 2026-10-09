import random
import string


def fake_token():
    token = "".join(random.choice(string.ascii_letters) for _ in range(16))
    return token


def test_fake_token_length():
    assert len(fake_token()) == 16
