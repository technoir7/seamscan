import subprocess
from pathlib import Path


def shallow_clone(repo_url: str, dest: Path, branch: str = "main") -> None:
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(dest)],
        check=True,
    )


def run_tool(args: list[str]) -> str:
    return subprocess.check_output(args, text=True)
