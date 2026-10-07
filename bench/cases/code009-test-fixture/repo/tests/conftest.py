import random
import string

import pytest


@pytest.fixture
def api_token() -> str:
    return "".join(random.choices(string.ascii_letters, k=24))
