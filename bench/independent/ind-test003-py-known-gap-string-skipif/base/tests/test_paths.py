from paths import to_posix


def test_to_posix():
    assert to_posix("a\\b") == "a/b"
