"""What a file is for (spec §5.6). Python-only so far; JS/TS roles arrive with M3."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    SERVER = "server"
    CLIENT = "client"
    TEST = "test"
    UNKNOWN = "unknown"


_TEST_DIRS = frozenset({"tests", "test", "__tests__"})


def role_of(path: str) -> Role:
    parts = path.split("/")
    name = parts[-1]
    if not name.endswith(".py"):
        return Role.UNKNOWN
    if (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
        or _TEST_DIRS.intersection(parts[:-1])
    ):
        return Role.TEST
    return Role.SERVER
