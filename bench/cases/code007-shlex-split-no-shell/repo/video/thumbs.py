import shlex
import subprocess


def thumbnail(src: str, out: str) -> None:
    subprocess.run(shlex.split(f"ffmpeg -i {src} -frames:v 1 {out}"), check=True)
