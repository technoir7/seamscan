"""I/O edge: decide which files to analyze and read them (spec §5.2)."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from seamscan.model import SourceFile

MAX_BYTES = 1_000_000
VENDOR_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "env",
        "dist",
        "build",
        ".next",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "coverage",
        ".turbo",
    }
)


@dataclass(frozen=True)
class FileSet:
    files: tuple[SourceFile, ...]
    skipped: tuple[tuple[str, str], ...]  # (path, reason) - reported in --stats, never silent


def _git_paths(root: Path) -> list[str] | None:
    try:
        out = subprocess.run(
            ["git", "-c", "core.quotePath=false", "ls-files", "-co", "--exclude-standard", "-z"],
            cwd=root,
            capture_output=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]


def _walk_paths(root: Path) -> list[str]:
    paths: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in VENDOR_DIRS)
        for name in filenames:
            paths.append((Path(dirpath) / name).relative_to(root).as_posix())
    return paths


def collect(root: Path, use_git: bool = True) -> FileSet:
    """Files under root: git's view (tracked + untracked, not ignored) when available."""
    paths = (_git_paths(root) if use_git else None) or _walk_paths(root)
    files: list[SourceFile] = []
    skipped: list[tuple[str, str]] = []
    for rel in sorted(paths):
        if VENDOR_DIRS.intersection(rel.split("/")[:-1]):
            continue
        full = root / rel
        if not full.is_file():
            continue
        if full.stat().st_size > MAX_BYTES:
            skipped.append((rel, "larger than 1 MB"))
            continue
        data = full.read_bytes()
        if b"\0" in data[:8192]:
            skipped.append((rel, "binary"))
            continue
        try:
            files.append(SourceFile(rel, data.decode("utf-8")))
        except UnicodeDecodeError:
            skipped.append((rel, "not UTF-8"))
    return FileSet(tuple(files), tuple(skipped))
