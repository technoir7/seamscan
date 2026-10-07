"""What a file is for: browser code, server code or tests (spec §5.6).

The first matching rule wins. Rules that depend on a role skip UNKNOWN files rather
than guess.
"""

from __future__ import annotations

import re
from enum import StrEnum

from seamscan.parse.javascript import JsModule, directive, js_dialect


class Role(StrEnum):
    SERVER = "server"
    CLIENT = "client"
    TEST = "test"
    UNKNOWN = "unknown"


_TEST_DIRS = frozenset({"tests", "test", "__tests__", "e2e", "cypress"})
_JS_TEST_NAME = re.compile(r"\.(?:test|spec)\.[cm]?[jt]sx?$")
_SERVER_DIRS = frozenset({"server", "api", "functions"})


def _is_test(parts: list[str]) -> bool:
    name = parts[-1]
    return bool(
        _TEST_DIRS.intersection(parts[:-1])
        or (name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py")))
        or name == "conftest.py"
        or _JS_TEST_NAME.search(name)
    )


def _js_role(parts: list[str], file_directive: str | None) -> Role:
    name = parts[-1]
    stem = name.split(".", 1)[0]
    dirs = parts[:-1]
    if file_directive == "use client":
        return Role.CLIENT
    if file_directive == "use server":
        return Role.SERVER
    # Next.js: route handlers, middleware, API routes and *.server.* modules run on the
    # server; anything else under app/ is a server component unless it says "use client".
    if (dirs and dirs[0] == "app" and stem == "route") or (not dirs and stem == "middleware"):
        return Role.SERVER
    if dirs[:2] == ["pages", "api"] or ".server." in name:
        return Role.SERVER
    if dirs and dirs[0] == "app":
        return Role.SERVER
    if dirs[:2] == ["supabase", "functions"]:  # Deno edge functions
        return Role.SERVER
    # Vite / Create React App: src/ ships to the browser except its server-side folders.
    if dirs and dirs[0] == "src":
        return Role.SERVER if _SERVER_DIRS.intersection(dirs[1:]) else Role.CLIENT
    return Role.UNKNOWN


def role_of(path: str, file_directive: str | None = None) -> Role:
    parts = path.split("/")
    if _is_test(parts):
        return Role.TEST
    if parts[-1].endswith(".py"):
        return Role.SERVER
    if js_dialect(path) is not None:
        return _js_role(parts, file_directive)
    return Role.UNKNOWN


def js_role(module: JsModule) -> Role:
    return role_of(module.path, directive(module))
