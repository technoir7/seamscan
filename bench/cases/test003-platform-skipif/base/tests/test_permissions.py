import sys

import pytest

from storage.files import write_private


def test_write_private_creates_file(tmp_path):
    assert write_private(tmp_path / "a.txt", "x").exists()
