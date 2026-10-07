"""I/O edge: ask git what changed (spec §5.5)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from seamscan.model import WHOLE_FILE, ChangeSet
from seamscan.parse.diff import parse_unified_diff


class GitError(RuntimeError):
    pass


def _git(root: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-c", "core.quotePath=false", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except FileNotFoundError as exc:
        raise GitError("git is not installed") from exc
    except subprocess.CalledProcessError as exc:
        first_line = (exc.stderr.strip().splitlines() or ["(no message)"])[0]
        raise GitError(f"git {args[0]} failed: {first_line}") from exc


def _require_repository(root: Path) -> None:
    try:
        _git(root, "rev-parse", "--is-inside-work-tree")
    except GitError as exc:
        raise GitError(
            f"{root} is not inside a git repository; use `seamscan audit` to check files directly"
        ) from exc


def read_changeset(root: Path, base: str | None = None, staged: bool = False) -> ChangeSet:
    """Changed lines against `base` (default HEAD), or the index with staged=True.

    Untracked files count as wholly added in working-tree scans; `git diff` omits them.
    """
    _require_repository(root)
    flags = ["--unified=0", "--no-color", "--no-ext-diff", "-M"]
    if staged:
        diff = _git(root, "diff", "--cached", *flags)
    else:
        diff = _git(root, "diff", *flags, base or "HEAD")
    change = parse_unified_diff(diff)
    if staged:
        return change
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    added = dict(change.added)
    for path in filter(None, untracked):
        added[path] = (WHOLE_FILE,)
    return ChangeSet(added=added)
