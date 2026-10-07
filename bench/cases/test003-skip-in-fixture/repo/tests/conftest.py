import os

import pytest


@pytest.fixture
def postgres_url():
    url = os.environ.get("TEST_DATABASE_URL")
    if url is None:
        pytest.skip("TEST_DATABASE_URL is not set")
    return url
