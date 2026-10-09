import pytest

from gpu import run_kernel


@pytest.mark.skip(
    reason="needs cuda"
)
def test_kernel():
    assert run_kernel() == 0
