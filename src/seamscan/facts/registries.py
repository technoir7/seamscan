"""Which package registries a repository uses besides the public ones (ADR-004). Pure.

Two facts matter to the dependency lookup:
- *private* names (an npm scope mapped to another registry, a uv or Poetry source) are
  never looked up, so they never leave the machine;
- an ecosystem with another registry configured makes a public 404 inconclusive: the
  package may live there.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, cast

from seamscan.facts.dependencies import pypi_name
from seamscan.model import Ecosystem, PackageRef, SourceFile

_PUBLIC_HOSTS = {
    Ecosystem.NPM: frozenset({"registry.npmjs.org", "registry.npmjs.com", "registry.yarnpkg.com"}),
    Ecosystem.PYPI: frozenset({"pypi.org", "pypi.python.org", "files.pythonhosted.org"}),
}
_HOST = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://(?:[^@/]*@)?([^/:?#]+)")
_SCOPE_REGISTRY = re.compile(r"^(@[^:\s]+):registry$")
# requirements*.txt, or any .txt in a requirements/ directory (where index options often
# sit in a shared base file).
_REQUIREMENTS = re.compile(r"(?:^|/)requirements(?:[^/]*|/[^/]+)\.txt$")
# pip options that add places to find packages; --find-links may name a local directory.
_INDEX_OPTION = re.compile(
    r"^(?:-i|--index-url|--extra-index-url|-f|--find-links)(?:\s*=\s*|\s+)(\S+)"
)


@dataclass(frozen=True)
class RegistryConfig:
    other_registries: frozenset[Ecosystem] = frozenset()  # a public 404 there is inconclusive
    private_scopes: frozenset[str] = frozenset()  # npm scopes, "@acme"
    private_names: frozenset[PackageRef] = frozenset()

    def is_private(self, ref: PackageRef) -> bool:
        """True when the name must not be sent to the public registry."""
        if ref in self.private_names:
            return True
        scope = ref.name.split("/", 1)[0]
        return ref.ecosystem is Ecosystem.NPM and "/" in ref.name and scope in self.private_scopes


def _public(ecosystem: Ecosystem, url: str) -> bool:
    m = _HOST.match(url.strip())
    return m is not None and m.group(1).lower() in _PUBLIC_HOSTS[ecosystem]


def _npmrc(text: str) -> tuple[bool, set[str]]:
    """(default registry is elsewhere, scopes mapped elsewhere). Auth lines are skipped
    unread: only registry keys matter, and tokens must not travel into findings."""
    other, scopes = False, set[str]()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")) or "=" not in line:
            continue
        key, value = (part.strip().strip("\"'") for part in line.split("=", 1))
        if key == "registry":
            other = other or not _public(Ecosystem.NPM, value)
        elif (m := _SCOPE_REGISTRY.match(key)) and not _public(Ecosystem.NPM, value):
            scopes.add(m.group(1))
    return other, scopes


def _requirements(text: str) -> bool:
    for raw in text.splitlines():
        m = _INDEX_OPTION.match(raw.strip())
        if m and not _public(Ecosystem.PYPI, m.group(1)):
            return True
    return False


def _table(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _tables(value: object) -> list[dict[str, Any]]:
    """An array of tables, or a single table, as a list of tables."""
    items = cast(list[Any], value) if isinstance(value, list) else [value]
    return [cast(dict[str, Any], t) for t in items if isinstance(t, dict)]


def _pyproject(text: str) -> tuple[bool, set[str]]:
    """(another index is configured, names pinned to a source other than the default)."""
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return False, set()  # ProjectModel reports unreadable manifests
    tool = _table(doc.get("tool"))
    uv, poetry = _table(tool.get("uv")), _table(tool.get("poetry"))
    indexes = [*_tables(uv.get("index")), *_tables(poetry.get("source"))]
    other = any(not _public(Ecosystem.PYPI, str(t.get("url", ""))) for t in indexes)
    # Any uv source (index, path, git, url, workspace) means the default index isn't where
    # the package comes from.
    names = set(_table(uv.get("sources")))
    groups = [poetry.get("dependencies")]
    groups += [g.get("dependencies") for g in _tables(list(_table(poetry.get("group")).values()))]
    for deps in groups:
        for name, spec in _table(deps).items():
            if any("source" in t for t in _tables(spec)):
                names.add(name)
    return other, names


def registry_config(files: Iterable[SourceFile]) -> RegistryConfig:
    other: set[Ecosystem] = set()
    scopes: set[str] = set()
    names: set[PackageRef] = set()
    for f in files:
        base = f.path.rsplit("/", 1)[-1]
        if base == ".npmrc":
            elsewhere, mapped = _npmrc(f.text)
            if elsewhere:
                other.add(Ecosystem.NPM)
            scopes |= mapped
        elif _REQUIREMENTS.search(f.path):
            if _requirements(f.text):
                other.add(Ecosystem.PYPI)
        elif base == "pyproject.toml":
            elsewhere, pinned = _pyproject(f.text)
            if elsewhere:
                other.add(Ecosystem.PYPI)
            names |= {PackageRef(Ecosystem.PYPI, pypi_name(n)) for n in pinned}
    return RegistryConfig(frozenset(other), frozenset(scopes), frozenset(names))
