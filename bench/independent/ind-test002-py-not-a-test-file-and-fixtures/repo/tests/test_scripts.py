import subprocess


def test_selfcheck_exits_zero():
    proc = subprocess.run(["python", "scripts/selfcheck.py"], capture_output=True)
    assert proc.returncode == 0
