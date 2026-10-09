"""Registry lookups at the I/O edge (spec §7.7 "Network behavior", ADR-004).

The network is a plain function passed in; these fakes answer by URL and record what was
asked, so every test also pins down how many requests a lookup costs.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from seamscan.model import Ecosystem, PackageFacts, PackageRef
from seamscan.supply.http import FetchError, Response
from seamscan.supply.registry import Lookup, Source, lookup, pinned_version
from seamscan.supply.snapshot import Snapshot

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
NPM = "https://registry.npmjs.org"
DOWNLOADS = "https://api.npmjs.org/downloads/point/last-week"
SIMPLE = "https://pypi.org/simple"
SIMPLE_JSON = "application/vnd.pypi.simple.v1+json"

Answer = Response | Exception


class FakeNet:
    def __init__(self, routes: Mapping[str, Answer | list[Answer]]):
        self.routes = {k: list(v) if isinstance(v, list) else [v] for k, v in routes.items()}
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, headers: Mapping[str, str]) -> Response:
        self.calls.append((url, dict(headers)))
        answers = self.routes.get(url)
        if not answers:
            raise AssertionError(f"unexpected request: {url}")
        answer = answers.pop(0) if len(answers) > 1 else answers[0]
        if isinstance(answer, Exception):
            raise answer
        return answer

    @property
    def urls(self) -> list[str]:
        return [url for url, _ in self.calls]


def no_network(url: str, headers: Mapping[str, str]) -> Response:
    raise AssertionError(f"offline lookup made a request: {url}")


def ok(doc: object) -> Response:
    return Response(200, json.dumps(doc).encode())


def npm(name: str) -> PackageRef:
    return PackageRef(Ecosystem.NPM, name)


def pypi(name: str) -> PackageRef:
    return PackageRef(Ecosystem.PYPI, name)


def packument(
    name: str,
    created: str = "2026-09-30T10:00:00.000Z",
    latest: str = "1.0.1",
    versions: Mapping[str, Mapping[str, object]] | None = None,
) -> Response:
    versions = versions or {"1.0.0": {}, latest: {"scripts": {"test": "jest"}}}
    return ok(
        {
            "name": name,
            "dist-tags": {"latest": latest},
            "time": {"created": created, "modified": created},
            "versions": {v: {"name": name, "version": v, **m} for v, m in versions.items()},
        }
    )


def downloads(name: str, n: int) -> Response:
    return ok({"downloads": n, "package": name, "start": "2026-10-01", "end": "2026-10-07"})


SNAPSHOT = Snapshot(
    {Ecosystem.NPM: frozenset({"react", "@types/node"}), Ecosystem.PYPI: frozenset({"requests"})}
)
EMPTY = Snapshot({})


def run(
    refs: Iterable[PackageRef],
    fetch: object,
    cache_dir: Path,
    *,
    offline: bool = False,
    now: datetime = NOW,
    snapshot: Snapshot = EMPTY,
    install_scripts: bool = False,
    versions: Mapping[PackageRef, str] | None = None,
    other_registries: frozenset[Ecosystem] = frozenset(),
    sleeps: list[float] | None = None,
) -> Lookup:
    slept = sleeps if sleeps is not None else []
    return lookup(
        refs,
        offline=offline,
        cache_dir=cache_dir,
        fetch=fetch,  # type: ignore[arg-type]
        now=now,
        snapshot=snapshot,
        install_scripts=install_scripts,
        versions=versions or {},
        other_registries=other_registries,
        sleep=slept.append,
    )


# --- npm -----------------------------------------------------------------------------------


def test_npm_missing_package_is_one_request(tmp_path: Path):
    net = FakeNet({f"{NPM}/react-codeshiftx": Response(404, b'{"error":"Not found"}')})
    result = run([npm("react-codeshiftx")], net, tmp_path)
    assert result.packages == {npm("react-codeshiftx"): PackageFacts(exists=False)}
    assert result.sources == {npm("react-codeshiftx"): Source.NETWORK}
    assert net.urls == [f"{NPM}/react-codeshiftx"]


def test_npm_existing_package_gets_age_and_downloads(tmp_path: Path):
    net = FakeNet(
        {
            f"{NPM}/left-padx": packument("left-padx", created="2026-10-01T08:30:00.000Z"),
            f"{DOWNLOADS}/left-padx": downloads("left-padx", 42),
        }
    )
    result = run([npm("left-padx")], net, tmp_path)
    assert result.packages[npm("left-padx")] == PackageFacts(
        exists=True,
        first_published=datetime(2026, 10, 1, 8, 30, tzinfo=UTC),
        weekly_downloads=42,
    )
    assert len(net.calls) == 2


def test_scoped_names_are_encoded_for_the_registry(tmp_path: Path):
    net = FakeNet(
        {
            f"{NPM}/@acme%2Fui": packument("@acme/ui"),
            f"{DOWNLOADS}/@acme/ui": downloads("@acme/ui", 500),
        }
    )
    assert run([npm("@acme/ui")], net, tmp_path).packages[npm("@acme/ui")].exists is True


def test_install_scripts_come_from_the_packument_without_another_request(tmp_path: Path):
    versions = {
        "1.0.0": {"scripts": {"postinstall": "node evil.js"}},
        "1.0.1": {"scripts": {"preinstall": "x", "install": "y", "test": "z"}},
    }
    net = FakeNet(
        {
            f"{NPM}/fresh-lib": packument("fresh-lib", versions=versions),
            f"{DOWNLOADS}/fresh-lib": downloads("fresh-lib", 3),
        }
    )
    latest = run([npm("fresh-lib")], net, tmp_path / "a", install_scripts=True)
    assert latest.packages[npm("fresh-lib")].install_scripts == ("preinstall", "install")
    pinned = run(
        [npm("fresh-lib")],
        net,
        tmp_path / "b",
        install_scripts=True,
        versions={npm("fresh-lib"): "1.0.0"},
    )
    assert pinned.packages[npm("fresh-lib")].install_scripts == ("postinstall",)
    assert len(net.calls) == 4


def test_audit_mode_leaves_install_scripts_unknown(tmp_path: Path):
    net = FakeNet(
        {f"{NPM}/fresh-lib": packument("fresh-lib"), f"{DOWNLOADS}/fresh-lib": downloads("x", 1)}
    )
    assert run([npm("fresh-lib")], net, tmp_path).packages[npm("fresh-lib")].install_scripts is None


def test_gypfile_means_npm_runs_node_gyp_at_install(tmp_path: Path):
    # npm runs `node-gyp rebuild` for a package with binding.gyp and no install hook; the
    # registry marks such versions with gypfile.
    versions = {"2.0.0": {"gypfile": True, "scripts": {"test": "t"}}}
    net = FakeNet(
        {
            f"{NPM}/native": packument("native", latest="2.0.0", versions=versions),
            f"{DOWNLOADS}/native": downloads("native", 5000),
        }
    )
    result = run([npm("native")], net, tmp_path, install_scripts=True)
    assert result.packages[npm("native")].install_scripts == ("install",)


def test_unpublished_package_does_not_exist(tmp_path: Path):
    doc = {"name": "gone", "time": {"created": "2020-01-01T00:00:00Z", "unpublished": {}}}
    net = FakeNet({f"{NPM}/gone": ok(doc)})
    assert run([npm("gone")], net, tmp_path).packages[npm("gone")] == PackageFacts(exists=False)


def test_no_download_stats_yet_counts_as_zero(tmp_path: Path):
    # api.npmjs.org has no entry for a package published hours ago.
    net = FakeNet(
        {
            f"{NPM}/brand-new": packument("brand-new"),
            f"{DOWNLOADS}/brand-new": Response(404, b'{"error":"package brand-new not found"}'),
        }
    )
    assert run([npm("brand-new")], net, tmp_path).packages[npm("brand-new")].weekly_downloads == 0


def test_snapshot_names_need_no_request(tmp_path: Path):
    result = run([npm("react"), pypi("requests")], no_network, tmp_path, snapshot=SNAPSHOT)
    assert result.packages == {
        npm("react"): PackageFacts(exists=True, popular=True),
        pypi("requests"): PackageFacts(exists=True, popular=True),
    }
    assert set(result.sources.values()) == {Source.SNAPSHOT}


def test_snapshot_names_added_in_a_change_fetch_only_the_version_document(tmp_path: Path):
    net = FakeNet(
        {
            f"{NPM}/@types%2Fnode/latest": ok({"name": "@types/node", "scripts": {}}),
            f"{NPM}/react/19.1.0": ok({"name": "react", "scripts": {"postinstall": "x"}}),
        }
    )
    result = run(
        [npm("react"), npm("@types/node")],
        net,
        tmp_path,
        snapshot=SNAPSHOT,
        install_scripts=True,
        versions={npm("react"): "19.1.0"},
    )
    assert result.packages == {
        npm("@types/node"): PackageFacts(exists=True, install_scripts=(), popular=True),
        npm("react"): PackageFacts(exists=True, install_scripts=("postinstall",), popular=True),
    }
    assert len(net.calls) == 2


@pytest.mark.parametrize(
    ("spec", "version"),
    [
        ("1.2.3", "1.2.3"),
        ("=1.2.3", "1.2.3"),
        ("v1.2.3", "1.2.3"),
        ("1.2.3-beta.1+build.5", "1.2.3-beta.1+build.5"),
        ("^1.2.3", None),
        ("~1.2.3", None),
        ("1.2.x", None),
        (">=1 <2", None),
        ("latest", None),
        ("", None),
    ],
)
def test_pinned_version(spec: str, version: str | None):
    assert pinned_version(spec) == version


# --- PyPI ----------------------------------------------------------------------------------


def simple(files: list[dict[str, object]]) -> Response:
    return ok({"meta": {"api-version": "1.4"}, "name": "x", "files": files, "versions": []})


def test_pypi_existence_and_first_upload_in_one_request(tmp_path: Path):
    files = [
        {"filename": "b-2.0.tar.gz", "upload-time": "2026-10-02T09:00:00.000000Z"},
        {"filename": "b-1.0.tar.gz", "upload-time": "2026-09-20T09:00:00.123456Z"},
        {"filename": "b-1.0-py3-none-any.whl"},  # upload-time is optional (PEP 700)
    ]
    net = FakeNet({f"{SIMPLE}/flask-loginx/": simple(files)})
    result = run([pypi("flask-loginx")], net, tmp_path)
    assert result.packages[pypi("flask-loginx")] == PackageFacts(
        exists=True, first_published=datetime(2026, 9, 20, 9, 0, 0, 123456, tzinfo=UTC)
    )
    assert net.calls == [(f"{SIMPLE}/flask-loginx/", {"Accept": SIMPLE_JSON})]


def test_pypi_missing_and_fileless_projects(tmp_path: Path):
    net = FakeNet(
        {f"{SIMPLE}/nope/": Response(404, b"404 Not Found"), f"{SIMPLE}/empty/": simple([])}
    )
    result = run([pypi("nope"), pypi("empty")], net, tmp_path)
    assert result.packages == {
        pypi("nope"): PackageFacts(exists=False),
        pypi("empty"): PackageFacts(exists=True),
    }


# --- failures are data ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("answer", "problem"),
    [
        (FetchError("timed out"), "registry.npmjs.org: timed out"),
        (FetchError("network error: nodename nor servname provided"), "network error"),
        (Response(503, b"<html>"), "HTTP 503 from registry.npmjs.org"),
        (Response(200, b"<html>not json"), "malformed response from registry.npmjs.org"),
        (Response(200, b'"a string"'), "malformed response from registry.npmjs.org"),
    ],
)
def test_failures_are_unverified_never_missing_or_existing(
    tmp_path: Path, answer: Answer, problem: str
):
    net = FakeNet({f"{NPM}/some-lib": answer})
    facts = run([npm("some-lib")], net, tmp_path).packages[npm("some-lib")]
    assert facts.exists is None
    assert problem in facts.problem
    assert not list(tmp_path.rglob("*.json")), "an unverified result must not be cached"


def test_rate_limit_backs_off_once_then_succeeds(tmp_path: Path):
    net = FakeNet(
        {
            f"{SIMPLE}/slow/": [Response(429, retry_after="2"), simple([])],
        }
    )
    sleeps: list[float] = []
    facts = run([pypi("slow")], net, tmp_path, sleeps=sleeps).packages[pypi("slow")]
    assert facts.exists is True
    assert sleeps == [2.0]


def test_rate_limit_twice_is_unverified_and_stops_asking_that_host(tmp_path: Path):
    net = FakeNet({f"{SIMPLE}/a/": Response(429), f"{SIMPLE}/b/": simple([])})
    sleeps: list[float] = []
    result = run([pypi("a"), pypi("b")], net, tmp_path, sleeps=sleeps)
    assert result.packages[pypi("a")].exists is None
    assert "rate limited by pypi.org (HTTP 429)" in result.packages[pypi("a")].problem
    assert result.packages[pypi("b")].exists is None
    assert net.urls == [f"{SIMPLE}/a/", f"{SIMPLE}/a/"]
    assert sleeps == [1.0]


def test_rate_limit_asking_for_a_long_wait_is_not_waited_out(tmp_path: Path):
    net = FakeNet({f"{SIMPLE}/a/": Response(429, retry_after="120")})
    sleeps: list[float] = []
    facts = run([pypi("a")], net, tmp_path, sleeps=sleeps).packages[pypi("a")]
    assert facts.exists is None and sleeps == []


def test_an_unreachable_host_is_not_retried_for_every_package(tmp_path: Path):
    # Forty dependencies must not cost forty timeouts.
    net = FakeNet({f"{NPM}/a": FetchError("timed out"), f"{SIMPLE}/p/": simple([])})
    result = run([npm("a"), npm("b"), pypi("p")], net, tmp_path)
    assert result.packages[npm("b")].exists is None
    assert "earlier in this run" in result.packages[npm("b")].problem
    assert result.packages[pypi("p")].exists is True
    assert net.urls == [f"{NPM}/a", f"{SIMPLE}/p/"]


def test_download_count_failure_keeps_what_was_verified_but_caches_nothing(tmp_path: Path):
    net = FakeNet({f"{NPM}/lib": packument("lib"), f"{DOWNLOADS}/lib": Response(500)})
    facts = run([npm("lib")], net, tmp_path).packages[npm("lib")]
    assert facts.exists is True and facts.first_published is not None
    assert facts.weekly_downloads is None
    assert not list(tmp_path.rglob("*.json"))


def test_a_404_where_another_registry_is_configured_is_unverified(tmp_path: Path):
    net = FakeNet({f"{NPM}/internal-lib": Response(404)})
    facts = run(
        [npm("internal-lib")], net, tmp_path, other_registries=frozenset({Ecosystem.NPM})
    ).packages[npm("internal-lib")]
    assert facts.exists is None
    assert "another npm registry" in facts.problem


# --- cache ---------------------------------------------------------------------------------


def lib_net() -> FakeNet:
    return FakeNet({f"{NPM}/lib": packument("lib"), f"{DOWNLOADS}/lib": downloads("lib", 7)})


def test_a_warm_cache_makes_no_requests(tmp_path: Path):
    net = FakeNet(
        {
            f"{NPM}/lib": packument("lib"),
            f"{DOWNLOADS}/lib": downloads("lib", 7),
            f"{NPM}/ghost": Response(404),
        }
    )
    first = run([npm("lib"), npm("ghost")], net, tmp_path)
    second = run([npm("lib"), npm("ghost")], no_network, tmp_path, now=NOW + timedelta(hours=23))
    assert second.packages == first.packages
    assert set(second.sources.values()) == {Source.CACHE}


def test_age_and_downloads_expire_after_a_day(tmp_path: Path):
    run([npm("lib")], lib_net(), tmp_path)
    net = lib_net()
    later = run([npm("lib")], net, tmp_path, now=NOW + timedelta(days=2))
    assert later.sources[npm("lib")] is Source.NETWORK
    assert len(net.calls) == 2


def test_existence_survives_a_failed_refresh_for_seven_days(tmp_path: Path):
    run([npm("lib")], lib_net(), tmp_path)
    down = FakeNet({f"{NPM}/lib": FetchError("timed out")})
    within = run([npm("lib")], down, tmp_path, now=NOW + timedelta(days=6))
    assert within.packages[npm("lib")] == PackageFacts(exists=True)
    assert within.sources[npm("lib")] is Source.CACHE
    after = run([npm("lib")], down, tmp_path, now=NOW + timedelta(days=8))
    assert after.packages[npm("lib")].exists is None


def test_install_scripts_for_another_version_are_fetched_on_their_own(tmp_path: Path):
    run([npm("lib")], lib_net(), tmp_path, install_scripts=True)
    net = FakeNet({f"{NPM}/lib/1.0.0": ok({"scripts": {"install": "x"}})})
    result = run([npm("lib")], net, tmp_path, install_scripts=True, versions={npm("lib"): "1.0.0"})
    assert result.packages[npm("lib")].install_scripts == ("install",)
    assert result.packages[npm("lib")].weekly_downloads == 7  # the rest from the cache
    assert net.urls == [f"{NPM}/lib/1.0.0"]


def test_a_corrupt_cache_file_is_ignored_and_replaced(tmp_path: Path):
    run([npm("lib")], lib_net(), tmp_path)
    (path,) = tmp_path.rglob("*.json")
    path.write_text('{"name": "lib", "checked": ')  # a crash mid-write by another tool
    net = lib_net()
    result = run([npm("lib")], net, tmp_path)
    assert result.packages[npm("lib")].exists is True and len(net.calls) == 2
    assert json.loads(path.read_text())["name"] == "lib"
    assert [p.name for p in tmp_path.rglob("*")] == ["npm", path.name], "no temp files left"


def test_an_unwritable_cache_is_a_warning_not_a_crash(tmp_path: Path):
    blocker = tmp_path / "cache"
    blocker.write_text("not a directory")
    result = run([npm("lib")], lib_net(), blocker)
    assert result.packages[npm("lib")].exists is True
    assert len(result.warnings) == 1 and "cache" in result.warnings[0]


# --- offline -------------------------------------------------------------------------------


def test_offline_uses_the_snapshot_and_the_cache_however_old(tmp_path: Path):
    run([npm("lib")], lib_net(), tmp_path)
    result = run(
        [npm("lib"), npm("react"), npm("unknown-lib")],
        no_network,
        tmp_path,
        offline=True,
        snapshot=SNAPSHOT,
        install_scripts=True,
        now=NOW + timedelta(days=60),
    )
    assert result.packages[npm("lib")].exists is True
    assert result.packages[npm("lib")].weekly_downloads == 7
    assert result.packages[npm("react")] == PackageFacts(exists=True, popular=True)
    assert result.packages[npm("unknown-lib")] == PackageFacts(
        exists=None, problem="offline; not in cache or snapshot"
    )
    assert result.sources == {
        npm("lib"): Source.CACHE,
        npm("react"): Source.SNAPSHOT,
        npm("unknown-lib"): Source.NONE,
    }


def test_timestamps_without_a_zone_are_unknown_not_a_crash(tmp_path: Path):
    files = [{"upload-time": "2026-09-20T09:00:00"}, {"upload-time": "yesterday"}]
    net = FakeNet({f"{SIMPLE}/odd/": simple(files)})
    assert run([pypi("odd")], net, tmp_path).packages[pypi("odd")] == PackageFacts(exists=True)


# --- the bundled snapshot ------------------------------------------------------------------


def test_bundled_snapshot_has_the_well_known_names_in_registry_form():
    from importlib.resources import files

    from seamscan.facts.dependencies import pypi_name
    from seamscan.supply.snapshot import bundled_snapshot

    snapshot = bundled_snapshot()
    for ref in (npm("react"), npm("@types/node"), pypi("requests"), pypi("flask-login")):
        assert ref in snapshot
    assert npm("react-codeshiftx") not in snapshot
    assert pypi("react") not in snapshot  # per ecosystem
    for eco in Ecosystem:
        lines = (files("seamscan.supply") / "data" / f"{eco.value}.txt").read_text().splitlines()
        assert lines == sorted(set(lines)) and 5_000 <= len(lines) <= 10_000
    assert all(pypi_name(n) == n for n in snapshot.names[Ecosystem.PYPI])
