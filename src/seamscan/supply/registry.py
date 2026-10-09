"""Turn package refs into registry facts: snapshot, then cache, then network (ADR-004).

Never raises for a network problem: a failure is `PackageFacts(exists=None, problem=...)`,
never "missing" and never "exists". Requests are sequential, in sorted order.

Cost per package not in the snapshot: npm, the packument (existence, first publish, and
the install scripts of the version checked) plus the weekly download count; PyPI, one
Simple API document (existence and first upload). A snapshot name costs nothing, except
in scan mode on npm, where its per-version document (a few KB, unlike a popular
packument's megabytes) gives the install scripts.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote, urlsplit

from seamscan.model import Ecosystem, PackageFacts, PackageRef
from seamscan.supply import cache
from seamscan.supply.cache import Record, Scripts
from seamscan.supply.http import Fetch, FetchError
from seamscan.supply.snapshot import Snapshot

NPM_REGISTRY = "https://registry.npmjs.org"
NPM_DOWNLOADS = "https://api.npmjs.org/downloads/point/last-week"
PYPI_SIMPLE = "https://pypi.org/simple"
SIMPLE_JSON = {"Accept": "application/vnd.pypi.simple.v1+json"}  # PEP 691

EXISTENCE_TTL = timedelta(days=7)
DETAIL_TTL = timedelta(days=1)  # first publish, downloads, install scripts
# A 429 is waited out once, and only for this long: the Stop hook has a time limit too.
MAX_RETRY_AFTER = 5.0
DEFAULT_RETRY_AFTER = 1.0
INSTALL_HOOKS = ("preinstall", "install", "postinstall")
OFFLINE_MISS = "offline; not in cache or snapshot"

_EXACT_VERSION = re.compile(r"^(?:=|v)?(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)$")


class Source(StrEnum):
    """Where a package's facts came from, for --stats."""

    NETWORK = "network"
    CACHE = "cache"
    SNAPSHOT = "snapshot"
    NONE = "none"  # nothing answered: the facts are unverified


@dataclass(frozen=True)
class Lookup:
    packages: dict[PackageRef, PackageFacts]
    sources: dict[PackageRef, Source]
    warnings: tuple[str, ...] = ()  # e.g. the cache couldn't be written; for stderr


def pinned_version(spec: str) -> str | None:
    """The exact version an npm spec pins, or None for a range or tag (checked as `latest`)."""
    m = _EXACT_VERSION.match(spec.strip())
    return m.group(1) if m else None


class _UnverifiedError(Exception):
    def __init__(self, problem: str):
        super().__init__(problem)
        self.problem = problem


@dataclass
class _Client:
    """Sequential GETs, with one wait on a 429 and a breaker per host: once a host has
    timed out, refused or rate-limited us, the rest of the run doesn't ask it again, so
    forty dependencies can't cost forty timeouts."""

    fetch: Fetch
    sleep: Callable[[float], None]
    down: dict[str, str] = field(default_factory=dict[str, str])

    def json(self, url: str, headers: Mapping[str, str] | None = None) -> Any:
        """The parsed body, or None for a 404. Raises _UnverifiedError for anything else."""
        host = urlsplit(url).hostname or url
        if host in self.down:
            raise _UnverifiedError(f"skipped: {self.down[host]} earlier in this run")
        for attempt in (1, 2):
            try:
                reply = self.fetch(url, headers or {})
            except FetchError as exc:
                self.down[host] = f"{host}: {exc}"
                raise _UnverifiedError(self.down[host]) from exc
            if reply.status != 429:
                break
            wait = _retry_after(reply.retry_after)
            if attempt == 2 or wait is None or wait > MAX_RETRY_AFTER:
                self.down[host] = f"rate limited by {host} (HTTP 429)"
                raise _UnverifiedError(self.down[host])
            self.sleep(wait)
        else:  # pragma: no cover - the loop always breaks or raises
            raise AssertionError
        if reply.status == 404:
            return None
        if reply.status != 200:
            raise _UnverifiedError(f"HTTP {reply.status} from {host}")
        try:
            doc = json.loads(reply.body)
        except ValueError as exc:
            raise _UnverifiedError(f"malformed response from {host}") from exc
        if not isinstance(doc, dict):
            raise _UnverifiedError(f"malformed response from {host}")
        return cast(dict[str, Any], doc)


def _retry_after(header: str | None) -> float | None:
    if header is None:
        return DEFAULT_RETRY_AFTER
    try:
        return max(0.0, float(header))
    except ValueError:
        return None  # an HTTP date: not worth parsing to then refuse the wait


def _fresh(checked: datetime | None, now: datetime, ttl: timedelta) -> bool:
    return checked is not None and timedelta(0) <= now - checked < ttl


def _date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    # Registries send UTC with a zone; a naive time couldn't be compared with `now`.
    return parsed if parsed.tzinfo is not None else None


def _hooks(manifest: object) -> tuple[str, ...]:
    """The install-time hooks a version's manifest declares, in the order npm runs them."""
    doc = cast(dict[str, Any], manifest) if isinstance(manifest, dict) else {}
    raw = doc.get("scripts")
    scripts = cast(dict[str, Any], raw) if isinstance(raw, dict) else {}
    hooks = {h for h in INSTALL_HOOKS if h in scripts}
    # npm runs `node-gyp rebuild` at install for a package with binding.gyp and no
    # install or preinstall hook of its own; the registry marks such versions `gypfile`.
    if doc.get("gypfile") is True and not hooks & {"install", "preinstall"}:
        hooks.add("install")
    return tuple(h for h in INSTALL_HOOKS if h in hooks)


@dataclass
class _Run:
    client: _Client
    offline: bool
    cache_dir: Path
    now: datetime
    snapshot: Snapshot
    install_scripts: bool
    versions: Mapping[PackageRef, str]
    warnings: list[str] = field(default_factory=list[str])

    def save(self, ref: PackageRef, record: Record) -> None:
        try:
            cache.write(self.cache_dir, ref, record)
        except OSError as exc:
            warning = f"could not write the registry cache in {self.cache_dir}: {exc.strerror}"
            if warning not in self.warnings:
                self.warnings.append(warning)

    def usable(self, checked: datetime | None, ttl: timedelta) -> bool:
        # Offline, any cached answer beats none: existence and first publish don't change,
        # and the online runs (CI, the Stop hook) refresh the rest.
        return checked is not None and (self.offline or _fresh(checked, self.now, ttl))

    # --- npm ---------------------------------------------------------------------------

    def npm(self, ref: PackageRef) -> tuple[PackageFacts, Source]:
        if ref in self.snapshot:
            popular = PackageFacts(exists=True, popular=True)
            if not self.install_scripts:
                return popular, Source.SNAPSHOT
            return self.npm_scripts(ref, popular, Source.SNAPSHOT, cache.read(self.cache_dir, ref))
        record = cache.read(self.cache_dir, ref)
        if (
            record is not None
            and record.exists is not None
            and self.usable(record.checked, DETAIL_TTL)
        ):
            facts = PackageFacts(record.exists, record.first_published, record.weekly_downloads)
            if not record.exists:
                return facts, Source.CACHE
            return self.npm_scripts(ref, facts, Source.CACHE, record)
        if self.offline:
            return PackageFacts(exists=None, problem=OFFLINE_MISS), Source.NONE
        try:
            return self.npm_fetch(ref)
        except _UnverifiedError as exc:
            return self.fallback(record, exc.problem)

    def npm_scripts(
        self, ref: PackageRef, facts: PackageFacts, source: Source, record: Record | None
    ) -> tuple[PackageFacts, Source]:
        """Add the install scripts of the version checked, when this run needs them."""
        if not self.install_scripts:
            return facts, source
        version = self.versions.get(ref, "latest")
        cached = record.scripts if record is not None else None
        if (
            cached is not None
            and cached.version == version
            and self.usable(cached.checked, DETAIL_TTL)
        ):
            return replace(facts, install_scripts=cached.hooks), Source.CACHE
        if self.offline:
            return facts, source
        try:
            doc = self.client.json(f"{NPM_REGISTRY}/{quote(ref.name, safe='@')}/{quote(version)}")
        except _UnverifiedError:
            return facts, source  # existence is settled; only the scripts stay unknown
        if doc is None:
            return facts, source  # no such version: npm install fails before any script
        hooks = _hooks(doc)
        self.save(ref, replace(record or Record(None), scripts=Scripts(version, self.now, hooks)))
        return replace(facts, install_scripts=hooks), Source.NETWORK

    def npm_fetch(self, ref: PackageRef) -> tuple[PackageFacts, Source]:
        doc = self.client.json(f"{NPM_REGISTRY}/{quote(ref.name, safe='@')}")
        versions = doc.get("versions") if doc is not None else None
        if doc is None or not isinstance(versions, dict) or not versions:
            # 404, or unpublished (the registry keeps a stub without versions)
            self.save(ref, Record(self.now, exists=False))
            return PackageFacts(exists=False), Source.NETWORK
        versions = cast(dict[str, Any], versions)
        times = doc.get("time")
        created = (
            _date(cast(dict[str, Any], times).get("created")) if isinstance(times, dict) else None
        )
        tags = doc.get("dist-tags")
        latest = cast(dict[str, Any], tags).get("latest") if isinstance(tags, dict) else None
        wanted = self.versions.get(ref) or latest
        version = self.versions.get(ref, "latest")
        hooks = _hooks(versions[wanted]) if isinstance(wanted, str) and wanted in versions else None
        facts = PackageFacts(exists=True, first_published=created)
        try:
            weekly = self.npm_downloads(ref)
        except _UnverifiedError:
            # Existence and age are verified; keep them for this run but cache nothing, so
            # the next run asks again rather than trusting a partial answer for a day.
            return replace(
                facts, install_scripts=hooks if self.install_scripts else None
            ), Source.NETWORK
        scripts = Scripts(version, self.now, hooks) if hooks is not None else None
        self.save(ref, Record(self.now, True, created, weekly, scripts))
        facts = replace(facts, weekly_downloads=weekly)
        if self.install_scripts:
            facts = replace(facts, install_scripts=hooks)
        return facts, Source.NETWORK

    def npm_downloads(self, ref: PackageRef) -> int:
        doc = self.client.json(f"{NPM_DOWNLOADS}/{quote(ref.name, safe='@/')}")
        if doc is None:
            return 0  # the stats service hasn't seen a package published hours ago
        count = doc.get("downloads")
        if not isinstance(count, int) or isinstance(count, bool):
            raise _UnverifiedError("malformed response from api.npmjs.org")
        return count

    # --- PyPI --------------------------------------------------------------------------

    def pypi(self, ref: PackageRef) -> tuple[PackageFacts, Source]:
        if ref in self.snapshot:
            return PackageFacts(exists=True, popular=True), Source.SNAPSHOT
        record = cache.read(self.cache_dir, ref)
        if (
            record is not None
            and record.exists is not None
            and self.usable(record.checked, DETAIL_TTL)
        ):
            return PackageFacts(record.exists, record.first_published), Source.CACHE
        if self.offline:
            return PackageFacts(exists=None, problem=OFFLINE_MISS), Source.NONE
        try:
            doc = self.client.json(f"{PYPI_SIMPLE}/{quote(ref.name)}/", SIMPLE_JSON)
        except _UnverifiedError as exc:
            return self.fallback(record, exc.problem)
        if doc is None:
            self.save(ref, Record(self.now, exists=False))
            return PackageFacts(exists=False), Source.NETWORK
        files = doc.get("files")
        if not isinstance(files, list):
            return self.fallback(record, "malformed response from pypi.org")
        uploads = [
            d
            for f in cast(list[Any], files)
            if isinstance(f, dict)
            and (d := _date(cast(dict[str, Any], f).get("upload-time"))) is not None
        ]
        first = min(uploads, default=None)
        self.save(ref, Record(self.now, True, first))
        return PackageFacts(exists=True, first_published=first), Source.NETWORK

    # --- shared ------------------------------------------------------------------------

    def fallback(self, record: Record | None, problem: str) -> tuple[PackageFacts, Source]:
        """After a failed refresh: a cached existence answer still holds for its TTL."""
        if (
            record is not None
            and record.exists is not None
            and _fresh(record.checked, self.now, EXISTENCE_TTL)
        ):
            return PackageFacts(exists=record.exists), Source.CACHE
        return PackageFacts(exists=None, problem=problem), Source.NONE


def lookup(
    refs: Iterable[PackageRef],
    *,
    offline: bool,
    cache_dir: Path,
    fetch: Fetch,
    now: datetime,
    snapshot: Snapshot,
    install_scripts: bool = False,
    versions: Mapping[PackageRef, str] | None = None,
    other_registries: frozenset[Ecosystem] = frozenset(),
    sleep: Callable[[float], None] = time.sleep,
) -> Lookup:
    """Facts for each ref.

    `install_scripts`: also read the install hooks of each npm package's checked version
    (the CLI asks in scan mode, where refs are only the dependencies the change adds).
    `versions`: exact versions pinned by the manifest; anything else is checked as `latest`.
    `other_registries`: ecosystems where the repository configures another registry, so a
    404 from the public one doesn't mean the package is missing.
    """
    run = _Run(
        _Client(fetch, sleep), offline, cache_dir, now, snapshot, install_scripts, versions or {}
    )
    packages: dict[PackageRef, PackageFacts] = {}
    sources: dict[PackageRef, Source] = {}
    for ref in sorted(set(refs)):
        facts, source = run.npm(ref) if ref.ecosystem is Ecosystem.NPM else run.pypi(ref)
        if facts.exists is False and ref.ecosystem in other_registries:
            public = "npm" if ref.ecosystem is Ecosystem.NPM else "PyPI"
            problem = f"not on public {public}; the repository also uses another {public} registry"
            facts = PackageFacts(exists=None, problem=problem)
        packages[ref], sources[ref] = facts, source
    return Lookup(packages, sources, tuple(run.warnings))
