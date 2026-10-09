import os

import pytest

from db import connect


@pytest.mark.skip(reason="needs the staging cluster")
def test_failover():
    conn = connect("primary")
    assert conn.ping()
