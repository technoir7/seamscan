import os

import pytest

from db import connect


@pytest.fixture
def postgres_url():
    if os.environ.get("TEST_DATABASE_URL") is None:
        pytest.skip("TEST_DATABASE_URL is not set")
    return os.environ["TEST_DATABASE_URL"]


@pytest.mark.skip(reason="needs the staging cluster")
def test_failover():
    conn = connect("primary", timeout=5)
    assert conn.ping()


def test_connects(postgres_url):
    assert connect(postgres_url).ping()
