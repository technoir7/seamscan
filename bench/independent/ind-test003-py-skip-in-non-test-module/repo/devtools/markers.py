import pytest

slow = pytest.mark.slow
skip_in_ci = pytest.mark.skip(reason="not run in ci")


def require_gpu():
    pytest.skip("no gpu")
