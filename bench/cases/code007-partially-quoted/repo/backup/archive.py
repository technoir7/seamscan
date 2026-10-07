import shlex
import subprocess


def make_archive(archive_name: str, source_dir: str) -> None:
    cmd = f"tar -czf {shlex.quote(archive_name)} {source_dir}"
    subprocess.run(cmd, shell=True, check=True)
