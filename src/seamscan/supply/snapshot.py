"""The bundled lists of the most-used npm and PyPI names (ADR-004; data/README.md).

A name on the list exists and is long established, so it needs no request for existence,
age or downloads. Loaded only when a run has dependencies to check.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from importlib.resources import files

from seamscan.model import Ecosystem, PackageRef


@dataclass(frozen=True)
class Snapshot:
    names: Mapping[Ecosystem, frozenset[str]]

    def __contains__(self, ref: PackageRef) -> bool:
        return ref.name in self.names.get(ref.ecosystem, frozenset())


@cache
def bundled_snapshot() -> Snapshot:
    data = files("seamscan.supply") / "data"
    return Snapshot(
        {
            eco: frozenset((data / f"{eco.value}.txt").read_text(encoding="utf-8").split())
            for eco in Ecosystem
        }
    )
