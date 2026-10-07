import shlex
import subprocess


def grep_logs(pattern: str, path: str) -> str:
    command = shlex.join(["grep", "-n", pattern, path]) + " | head -50"
    return subprocess.run(command, shell=True, capture_output=True, text=True).stdout
