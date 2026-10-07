import shutil

import pytest

requires_docker = pytest.mark.skipif(
    shutil.which("docker") is None, reason="docker is not installed"
)
