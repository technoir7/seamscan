import sys

import pytest

from storage.files import write_private


def test_write_private_creates_file(tmp_path):
    assert write_private(tmp_path / "a.txt", "x").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes")
def test_write_private_sets_mode_600(tmp_path):
    path = write_private(tmp_path / "secret.txt", "x")
    assert path.stat().st_mode & 0o777 == 0o600
