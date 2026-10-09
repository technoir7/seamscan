import re

SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9]{24,}"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


def scrub(line: str) -> str:
    for pat in SECRET_PATTERNS:
        line = pat.sub("[redacted]", line)
    return line
