import subprocess


def clone(repo_url: str, dest: str) -> None:
    subprocess.run(["git", "clone", "--depth", "1", "--", repo_url, dest], check=True)
