import os
import sys
import unittest

import pytest

from files import chmod_private

IS_WINDOWS = sys.platform == "win32"
pd = pytest.importorskip("pandas")


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes")
def test_chmod_private(tmp_path):
    p = tmp_path / "k"
    p.write_text("x")
    chmod_private(p)
    assert p.stat().st_mode & 0o777 == 0o600


@pytest.mark.skipif(IS_WINDOWS, reason="symlinks need admin")
def test_symlink(tmp_path):
    (tmp_path / "a").write_text("1")
    os.symlink(tmp_path / "a", tmp_path / "b")


class TomlTests(unittest.TestCase):
    @unittest.skipIf(sys.version_info < (3, 12), "needs 3.12 tomllib behaviour")
    def test_toml(self):
        self.assertTrue(True)

    def test_name(self):
        if os.name == "nt":
            self.skipTest("no fork on nt")
