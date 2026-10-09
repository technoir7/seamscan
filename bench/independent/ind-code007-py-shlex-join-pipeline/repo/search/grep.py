import shlex
import subprocess


def find_matches(pattern: str, path: str) -> str:
    cmd = shlex.join(["grep", "-n", "--", pattern, path]) + " | head -50"
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
