import shlex
import subprocess


def resize(src: str, dst: str, width: int) -> None:
    cmd = f"convert {shlex.quote(src)} -resize {int(width)}x {shlex.quote(dst)}"
    subprocess.run(cmd, shell=True, check=True)
