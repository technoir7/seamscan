import logging
import re

# Scrub anything credential-shaped before it reaches the log aggregator.
SECRET_PATTERNS = [
    re.compile(r"(sk|rk)_live_[0-9a-zA-Z]{24,}"),
    re.compile(r"sk-(proj-|ant-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36}"),
    re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


class RedactSecrets(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for pattern in SECRET_PATTERNS:
            message = pattern.sub("[REDACTED]", message)
        record.msg, record.args = message, None
        return True
