import subprocess

DISK_CMD = "df -h / | tail -1"


def error_count() -> int:
    out = subprocess.check_output("journalctl -u app | grep -c ERROR", shell=True, text=True)
    return int(out)


def disk() -> str:
    return subprocess.check_output(DISK_CMD, shell=True, text=True)
