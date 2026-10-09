"""Registry answers on disk, one JSON file per package (spec §7.7 "Network behavior").

Only verified answers are written. Writes go through a temporary file and a rename, so a
concurrent run never reads half a file; a file that doesn't parse is treated as absent
and overwritten by the next verified answer.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote

from seamscan.model import PackageRef

_FORMAT = 1


@dataclass(frozen=True)
class Scripts:
    version: str  # the version or dist-tag they were read for ("latest", "1.2.3")
    checked: datetime
    hooks: tuple[str, ...]


@dataclass(frozen=True)
class Record:
    checked: datetime | None  # when existence, age and downloads were fetched; None if never
    exists: bool | None = None
    first_published: datetime | None = None
    weekly_downloads: int | None = None
    scripts: Scripts | None = None


def _path(directory: Path, ref: PackageRef) -> Path:
    # quote keeps scoped names ("@types/node") to one file. Case-insensitive filesystems
    # can fold two legacy npm names together, so the file also records the exact name.
    return directory / ref.ecosystem.value / f"{quote(ref.name, safe='@')}.json"


def _time(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("not a timestamp")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp without a time zone")  # can't be compared with `now`
    return parsed


def _bool(value: object) -> bool | None:
    if value is not None and not isinstance(value, bool):
        raise ValueError("not a boolean")
    return value


def _int(value: object) -> int | None:
    if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
        raise ValueError("not an integer")
    return value


def read(directory: Path, ref: PackageRef) -> Record | None:
    """The cached record, or None when there is none or it can't be trusted."""
    try:
        doc = json.loads(_path(directory, ref).read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            return None
        doc = cast(dict[str, Any], doc)
        if doc.get("format") != _FORMAT or doc.get("name") != ref.name:
            return None
        scripts = None
        raw_scripts = doc.get("scripts")
        if raw_scripts is not None:
            s = cast(dict[str, Any], raw_scripts) if isinstance(raw_scripts, dict) else {}
            hooks = s.get("hooks")
            checked = _time(s.get("checked"))
            if (
                not isinstance(s.get("version"), str)
                or checked is None
                or not isinstance(hooks, list)
            ):
                return None
            hooks = cast(list[Any], hooks)
            if not all(isinstance(h, str) for h in hooks):
                return None
            scripts = Scripts(s["version"], checked, tuple(cast(list[str], hooks)))
        return Record(
            checked=_time(doc.get("checked")),
            exists=_bool(doc.get("exists")),
            first_published=_time(doc.get("first_published")),
            weekly_downloads=_int(doc.get("weekly_downloads")),
            scripts=scripts,
        )
    except (OSError, ValueError):  # missing, unreadable or corrupt: refetch and overwrite
        return None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def write(directory: Path, ref: PackageRef, record: Record) -> None:
    """Raises OSError when the cache can't be written; the caller decides how loud to be."""
    path = _path(directory, ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "format": _FORMAT,
        "name": ref.name,
        "checked": _iso(record.checked),
        "exists": record.exists,
        "first_published": _iso(record.first_published),
        "weekly_downloads": record.weekly_downloads,
        "scripts": None
        if record.scripts is None
        else {
            "version": record.scripts.version,
            "checked": _iso(record.scripts.checked),
            "hooks": list(record.scripts.hooks),
        },
    }
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(doc, out, sort_keys=True)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
