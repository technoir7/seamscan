import shlex
import subprocess


def make_archive(name: str, src_dir: str) -> None:
    subprocess.run(f"tar -czf {shlex.quote(name)} {src_dir}", shell=True, check=True)
