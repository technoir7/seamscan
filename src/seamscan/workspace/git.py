"""I/O edge: ask git what changed (spec §5.5)."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from seamscan.model import WHOLE_FILE, ChangeSet
from seamscan.parse.diff import parse_unified_diff


class GitError(RuntimeError):
    pass


def _git(root: Path, *args: str) -> str:
    try:
        return subprocess.run(
            # Literal pathspecs: a file named `a[1].py` means that file, not a glob.
            ["git", "-c", "core.quotePath=false", "--literal-pathspecs", *args],
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


def repo_root(start: Path) -> Path:
    """The top of the working tree that contains `start`."""
    _require_repository(start)
    return Path(_git(start, "rev-parse", "--show-toplevel").strip())


def unknown_paths(root: Path, paths: Sequence[str]) -> tuple[str, ...]:
    """The repo-relative paths that are neither tracked nor untracked-and-not-ignored."""
    listed = _git(
        root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", *paths
    )
    known = set(filter(None, listed.split("\0")))
    return tuple(
        p for p in paths if p not in known and not any(k.startswith(p + "/") for k in known)
    )


def read_changeset(
    root: Path, base: str | None = None, staged: bool = False, paths: Sequence[str] = ()
) -> ChangeSet:
    """Changed lines against `base` (default HEAD), or the index with staged=True.

    Untracked files count as wholly added in working-tree scans; `git diff` omits them.
    With `paths`, only changes to those files (repo-relative) count.
    """
    _require_repository(root)
    flags = ["--unified=0", "--no-color", "--no-ext-diff", "-M"]
    limit = ["--", *paths] if paths else []
    if staged:
        diff = _git(root, "diff", "--cached", *flags, *limit)
    else:
        diff = _git(root, "diff", *flags, base or "HEAD", *limit)
    change = parse_unified_diff(diff)
    if staged:
        return change
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z", *limit).split("\0")
    added = dict(change.added)
    for path in filter(None, untracked):
        added[path] = (WHOLE_FILE,)
    return ChangeSet(added=added)


def read_file_at(root: Path, ref: str, path: str) -> str | None:
    """The text of `path` (relative to `root`) as committed at `ref`; None if absent there."""
    _require_repository(root)
    if ref.startswith("-"):
        raise GitError(f"not a git ref: {ref!r}")
    try:
        _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    except GitError as exc:
        raise GitError(f"unknown git ref: {ref}") from exc
    # `<ref>:./<path>` resolves against the working directory, so a root below the
    # repository top still names the right file.
    spec = f"{ref}:./{path}"
    exists = subprocess.run(["git", "cat-file", "-e", spec], cwd=root, capture_output=True)
    if exists.returncode != 0:
        return None
    return _git(root, "show", spec)
