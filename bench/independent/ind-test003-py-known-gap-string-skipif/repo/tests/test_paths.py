import pytest

from paths import to_posix


@pytest.mark.skipif("sys.platform == 'win32'", reason="posix only")
def test_to_posix():
    assert to_posix("a\\b") == "a/b"
