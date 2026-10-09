import shlex
import subprocess


def thumbnail(src: str, dst: str, width: int) -> None:
    subprocess.run(
        f"convert {shlex.quote(src)} -resize {int(width)}x {shlex.quote(dst)}",
        shell=True,
        check=True,
    )
