"""Dependencies declared in manifests, with exact locations (spec §7.7, ADR-004). Pure.

The registry lookups happen at the I/O edge (`supply/`); this module only says which
packages a repository asks for and where.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, cast

from seamscan.model import ChangeSet, Ecosystem, Location, PackageRef, SourceFile

_NPM_SECTIONS = ("dependencies", "devDependencies", "optionalDependencies")
_REQUIREMENTS = re.compile(r"(?:^|/)requirements[^/]*\.txt$")
_PEP508_NAME = re.compile(r"\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*(?:\[[^\]]*\])?")


@dataclass(frozen=True)
class Dependency:
    ref: PackageRef
    spec: str  # version range or specifier as written ("^19.0.0", "==0.6.3", "")
    location: Location


def pypi_name(name: str) -> str:
    """PEP 503 normalization: the registry treats Flask_Login and flask-login as one."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _position(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    return line, offset - (text.rfind("\n", 0, offset) + 1) + 1


def _package_json(f: SourceFile) -> list[Dependency]:
    try:
        data = json.loads(f.text)
    except json.JSONDecodeError:
        return []  # ProjectModel reports unreadable manifests
    if not isinstance(data, dict):
        return []
    manifest = cast(dict[str, Any], data)
    found: list[Dependency] = []
    for section in _NPM_SECTIONS:
        raw_entries = manifest.get(section)
        if not isinstance(raw_entries, dict):
            continue
        entries = cast(dict[str, Any], raw_entries)
        # json gives no positions, so find each key lexically inside its section's braces.
        head = re.search(rf'"{section}"\s*:\s*\{{', f.text)
        if head is None:
            continue
        end = f.text.find("}", head.end())
        for name, spec in entries.items():
            key = re.compile(rf'"{re.escape(name)}"\s*:')
            m = key.search(f.text, head.end(), end)
            if m is None:
                continue
            line, col = _position(f.text, m.start())
            loc = Location(f.path, line, col, line, col + len(m.group(0)))
            found.append(Dependency(PackageRef(Ecosystem.NPM, name), str(spec), loc))
    return found


def _requirements(f: SourceFile) -> list[Dependency]:
    found: list[Dependency] = []
    for number, raw in enumerate(f.text.splitlines(), start=1):
        line = raw.split(" #", 1)[0].strip()
        # Options (-r, -e, --index-url), URLs and paths aren't registry packages.
        if not line or line.startswith(("#", "-", ".", "/")) or "://" in line:
            continue
        m = _PEP508_NAME.match(line)
        if m is None:
            continue
        spec = line[m.end() :].split(";", 1)[0].strip()
        col = raw.index(m.group(1)) + 1
        loc = Location(f.path, number, col, number, col + len(m.group(1)))
        found.append(Dependency(PackageRef(Ecosystem.PYPI, pypi_name(m.group(1))), spec, loc))
    return found


def declared_dependencies(files: Iterable[SourceFile]) -> tuple[Dependency, ...]:
    found: list[Dependency] = []
    for f in sorted(files, key=lambda f: f.path):
        if f.path == "package.json" or f.path.endswith("/package.json"):
            found.extend(_package_json(f))
        elif _REQUIREMENTS.search(f.path):
            found.extend(_requirements(f))
    return tuple(found)


def dependencies_to_check(
    files: Iterable[SourceFile], change: ChangeSet | None
) -> frozenset[PackageRef]:
    """The packages worth a registry lookup: in scan mode, only those on added lines."""
    return frozenset(
        d.ref
        for d in declared_dependencies(files)
        if change is None
        or change.touches(d.location.path, d.location.start_line, d.location.end_line)
    )
