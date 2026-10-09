import subprocess


def recent_commits(branch: str, count: int = 10) -> str:
    cmd = f"git log --oneline -n {count} {branch}"
    return subprocess.check_output(cmd, shell=True, text=True)
