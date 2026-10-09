from files import chmod_private


def test_chmod_private(tmp_path):
    p = tmp_path / "k"
    p.write_text("x")
    chmod_private(p)
    assert p.stat().st_mode & 0o777 == 0o600
