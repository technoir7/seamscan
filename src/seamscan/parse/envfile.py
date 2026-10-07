""".env text -> key/value entries (spec §5.2). Values may be secrets: never print them."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

_ASSIGNMENT = re.compile(r"[ \t]*(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_.]*)[ \t]*=")
_INLINE_COMMENT = re.compile(r"[ \t]#")


@dataclass(frozen=True)
class EnvEntry:
    key: str
    value: str  # quotes removed, escapes left as written
    line: int  # 1-based, where the value starts
    col: int  # 1-based, where the value starts (inside the quotes, if quoted)


def _closing_quote(text: str, quote: str) -> int:
    i = 0
    while i < len(text):
        if text[i] == "\\" and quote == '"':
            i += 2
            continue
        if text[i] == quote:
            return i
        i += 1
    return -1


def _quoted(first: str, following: Sequence[str], quote: str) -> tuple[str, int] | None:
    """The quoted value and how many extra lines it spans; None when the quote never closes."""
    text = first
    for extra in range(len(following) + 1):
        if extra:
            text += "\n" + following[extra - 1]
        end = _closing_quote(text, quote)
        if end >= 0:
            return text[:end], extra
    return None


def parse_env(text: str) -> tuple[EnvEntry, ...]:
    """KEY=VALUE entries in dotenv syntax: `export`, quotes, multi-line quoted values and
    `#` comments. Lines that are not assignments are skipped, as dotenv itself does."""
    lines = text.splitlines()
    entries: list[EnvEntry] = []
    i = 0
    while i < len(lines):
        line, number = lines[i], i + 1
        i += 1
        m = _ASSIGNMENT.match(line)
        if not m:
            continue
        rest = line[m.end() :]
        start = m.end() + len(rest) - len(rest.lstrip(" \t"))
        stripped = line[start:]
        if stripped[:1] in ('"', "'"):
            quoted = _quoted(stripped[1:], lines[i:], stripped[0])
            if quoted is not None:
                value, extra = quoted
                entries.append(EnvEntry(m.group(1), value, number, start + 2))
                i += extra
                continue
            # An unterminated quote is read as an unquoted value rather than dropped,
            # so a typo can't hide a secret from the rules.
        comment = _INLINE_COMMENT.search(rest)
        value = (rest[: comment.start()] if comment else rest).strip()
        entries.append(EnvEntry(m.group(1), value, number, start + 1))
    return tuple(entries)
