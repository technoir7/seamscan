import platform

import pytest

from gpu import run_kernel


@pytest.mark.skip(
    reason="needs a CUDA device, tracked in #231"
)
def test_kernel():
    assert run_kernel() == 0


@pytest.mark.skipif(platform.system() == "Darwin", reason="no metal backend")
def test_kernel_metal():
    assert run_kernel("metal") == 0
