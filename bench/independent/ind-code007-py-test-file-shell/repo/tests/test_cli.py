import os


def test_cli_creates_file(tmp_path):
    target = tmp_path / "out.txt"
    os.system(f"python -m tool --out {target}")
    assert target.exists()
