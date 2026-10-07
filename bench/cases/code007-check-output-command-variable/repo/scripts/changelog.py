import subprocess


def recent_commits(branch: str, count: int = 20) -> list[str]:
    cmd = f"git log --oneline -n {count} {branch}"
    out = subprocess.check_output(cmd, shell=True, text=True)
    return out.splitlines()
