import subprocess

REPO = "acme/internal-tools"


def pull_latest(dest: str) -> None:
    url = f"https://deploybot:{{FAKE_GITHUB_PAT}}@github.com/{REPO}.git"
    subprocess.run(["git", "clone", "--depth", "1", url, dest], check=True)
