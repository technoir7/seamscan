import subprocess

DISK_CMD = "df -h / | tail -1"


def recent_errors() -> str:
    return subprocess.check_output(
        "journalctl -u app --since '1 hour ago' | grep -c ERROR", shell=True, text=True
    )


def disk_line() -> str:
    return subprocess.check_output(DISK_CMD, shell=True, text=True).strip()
