"""Dependency lookups wired through the CLI (spec §7.7, §11, ADR-004).

The registry is a fake fetch function swapped in for `seamscan.cli.fetch_url`; the cache
lives under a temporary XDG_CACHE_HOME (see conftest.py).
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest
from typer.testing import CliRunner

import seamscan.cli
from seamscan.cli import app
from seamscan.model import Confidence, Finding, Location, Severity
from seamscan.rules.base import Rule, RuleContext, finding, meta
from seamscan.supply.http import FetchError, Response

runner = CliRunner()
NPM = "https://registry.npmjs.org"
DOWNLOADS = "https://api.npmjs.org/downloads/point/last-week"

PROBE = meta("SC-META-998", "probe", Severity.LOW, Confidence.LOW, (), frozenset(), "")
# On the first dependency's line, so scan mode keeps the finding when that line is added.
AT = Location("package.json", 4, 1, 4, 1)


def report_registry(ctx: RuleContext) -> list[Finding]:
    """Stands in for the dependency rules: one finding describing the view it was given."""
    view = ctx.registry
    if view is None:
        return [finding(PROBE, AT, "no registry view", "")]
    facts = {
        f"{ref.ecosystem.value}:{ref.name}": [f.exists, f.popular, f.install_scripts, f.problem]
        for ref, f in sorted(view.packages.items())
    }
    message = json.dumps(
        {"packages": facts, "thresholds": [view.min_age_days, view.min_weekly_downloads]}
    )
    return [finding(PROBE, AT, message, "")]


class FakeNet:
    def __init__(self, routes: Mapping[str, Response | Exception]):
        self.routes = routes
        self.urls: list[str] = []

    def __call__(self, url: str, headers: Mapping[str, str]) -> Response:
        self.urls.append(url)
        answer = self.routes.get(url)
        if answer is None:
            raise AssertionError(f"unexpected request: {url}")
        if isinstance(answer, Exception):
            raise answer
        return answer


def ok(doc: object) -> Response:
    return Response(200, json.dumps(doc).encode())


def packument(name: str, scripts: Mapping[str, str] | None = None) -> Response:
    return ok(
        {
            "name": name,
            "dist-tags": {"latest": "1.0.0"},
            "time": {"created": "2026-10-08T00:00:00Z"},
            "versions": {"1.0.0": {"scripts": dict(scripts or {})}},
        }
    )


LEFT_PADX = {
    f"{NPM}/left-padx": packument("left-padx"),
    f"{DOWNLOADS}/left-padx": ok({"downloads": 3}),
}


@pytest.fixture
def probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(seamscan.cli, "RULES", (Rule(PROBE, report_registry),))


def use_net(monkeypatch: pytest.MonkeyPatch, routes: Mapping[str, Response | Exception]) -> FakeNet:
    net = FakeNet(routes)
    monkeypatch.setattr(seamscan.cli, "fetch_url", net)
    return net


def package_json(root: Path, deps: Mapping[str, str]) -> None:
    (root / "package.json").write_text(
        json.dumps({"name": "app", "dependencies": dict(deps)}, indent=2) + "\n"
    )


def seen_by_rules(stdout: str) -> dict[str, object]:
    (probe_finding,) = [f for f in json.loads(stdout)["findings"] if f["rule_id"] == PROBE.id]
    return json.loads(probe_finding["message"])


def audit(root: Path, *extra: str) -> object:
    return runner.invoke(app, ["audit", str(root), "--format", "json", *extra])


# --- audit -----------------------------------------------------------------------------


@pytest.mark.usefixtures("probe")
def test_audit_looks_up_declared_dependencies_and_passes_the_view_to_the_rules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    package_json(tmp_path, {"react": "^19.0.0", "left-padx": "^1.0.0"})
    net = use_net(monkeypatch, LEFT_PADX)
    result = audit(tmp_path, "--stats")
    assert result.exit_code == 0, result.output
    assert seen_by_rules(result.stdout) == {
        "packages": {
            "npm:left-padx": [True, False, None, ""],
            "npm:react": [True, True, None, ""],  # the snapshot: no request
        },
        "thresholds": [30, 100],
    }
    assert net.urls == [f"{NPM}/left-padx", f"{DOWNLOADS}/left-padx"]
    assert "dependencies checked: 2 (network 1, cache 0, snapshot 1)" in result.stderr


@pytest.mark.usefixtures("probe")
def test_a_second_run_answers_from_the_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _isolated_registry: Path
):
    package_json(tmp_path, {"left-padx": "^1.0.0"})
    use_net(monkeypatch, LEFT_PADX)
    audit(tmp_path)
    assert list((_isolated_registry / "seamscan" / "registry").rglob("left-padx.json"))
    net = use_net(monkeypatch, {})
    result = audit(tmp_path, "--stats")
    assert net.urls == []
    assert "dependencies checked: 1 (network 0, cache 1, snapshot 0)" in result.stderr


@pytest.mark.usefixtures("probe")
def test_offline_never_touches_the_network(tmp_path: Path):
    # conftest's fetch fails the test if called
    package_json(tmp_path, {"react": "^19.0.0", "left-padx": "^1.0.0"})
    result = audit(tmp_path, "--offline", "--stats")
    assert result.exit_code == 0, result.output
    assert seen_by_rules(result.stdout)["packages"] == {
        "npm:left-padx": [None, False, None, "offline; not in cache or snapshot"],
        "npm:react": [True, True, None, ""],
    }
    assert "not verified: 1" in result.stderr


@pytest.mark.usefixtures("probe")
def test_allowed_and_privately_mapped_names_never_leave_the_machine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    package_json(tmp_path, {"@acme/ui": "^1.0.0", "acme-tools": "1.0.0", "left-padx": "1.0.0"})
    (tmp_path / ".npmrc").write_text("@acme:registry=https://npm.acme.internal/\n")
    (tmp_path / "seamscan.toml").write_text(
        "[deps]\nallow = ['acme-*']\nmin_age_days = 7\nmin_weekly_downloads = 10\n"
    )
    net = use_net(monkeypatch, LEFT_PADX)
    result = audit(tmp_path, "--stats")
    assert net.urls == [f"{NPM}/left-padx", f"{DOWNLOADS}/left-padx"]
    seen = seen_by_rules(result.stdout)
    assert list(seen["packages"]) == ["npm:left-padx"]  # type: ignore[arg-type]
    assert seen["thresholds"] == [7, 10]
    assert "not looked up (allowed or private): 2" in result.stderr


@pytest.mark.usefixtures("probe")
def test_a_404_in_a_repository_with_another_registry_is_unverified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    package_json(tmp_path, {"internal-lib": "1.0.0"})
    (tmp_path / ".npmrc").write_text("registry=https://npm.acme.internal/\n")
    use_net(monkeypatch, {f"{NPM}/internal-lib": Response(404)})
    result = audit(tmp_path, "--stats")
    packages = seen_by_rules(result.stdout)["packages"]
    assert packages["npm:internal-lib"][0] is None  # type: ignore[index]
    assert "not verified: 1" in result.stderr


def test_an_unwritable_cache_is_reported_and_the_run_goes_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    blocked = tmp_path / "blocked"
    blocked.write_text("a file where the cache directory should be")
    monkeypatch.setenv("XDG_CACHE_HOME", str(blocked))
    project = tmp_path / "project"
    project.mkdir()
    package_json(project, {"left-padx": "1.0.0"})
    use_net(monkeypatch, LEFT_PADX)
    result = audit(project)
    assert result.exit_code == 0
    assert "could not write the registry cache" in result.stderr


def test_the_real_rules_run_with_a_registry_view(tmp_path: Path):
    # Without the probe: whatever dependency rules exist must cope with an offline miss.
    package_json(tmp_path, {"left-padx": "1.0.0"})
    result = audit(tmp_path, "--offline")
    assert result.exit_code == 0, result.output


# --- scan and the hook -----------------------------------------------------------------


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    package_json(root, {"react": "^19.0.0"})
    git(root, "add", ".")
    git(root, "commit", "-qm", "init")
    monkeypatch.chdir(root)
    return root


@pytest.mark.usefixtures("probe")
def test_scan_checks_only_added_dependencies_with_their_install_scripts(
    repo: Path, monkeypatch: pytest.MonkeyPatch
):
    # New entries go first: appending would add a comma to react's line, and touch it.
    package_json(repo, {"left-padx": "^1.0.0", "esbuild": "0.25.0", "react": "^19.0.0"})
    net = use_net(
        monkeypatch,
        {
            f"{NPM}/left-padx": packument("left-padx", {"postinstall": "node x.js"}),
            f"{DOWNLOADS}/left-padx": ok({"downloads": 3}),
            f"{NPM}/esbuild/0.25.0": ok({"scripts": {"postinstall": "node install.js"}}),
        },
    )
    result = runner.invoke(app, ["scan", "--format", "json"])
    assert seen_by_rules(result.stdout)["packages"] == {
        "npm:esbuild": [True, True, ["postinstall"], ""],
        "npm:left-padx": [True, False, ["postinstall"], ""],
    }
    assert f"{NPM}/react" not in "".join(net.urls)


def test_scan_never_looks_up_a_package_defined_elsewhere_in_the_repository(
    repo: Path, monkeypatch: pytest.MonkeyPatch
):
    # The workspace package lives in an unchanged file; only the whole repository shows
    # that `@acme/ui` is local, so its name must not reach the public registry.
    (repo / "packages" / "ui").mkdir(parents=True)
    (repo / "packages" / "ui" / "package.json").write_text(json.dumps({"name": "@acme/ui"}))
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "workspace")
    package_json(repo, {"@acme/ui": "^1.0.0", "react": "^19.0.0"})
    net = use_net(monkeypatch, {})
    result = runner.invoke(app, ["scan", "--format", "json"])
    assert result.exit_code == 0, result.output
    assert net.urls == []


def test_an_import_of_a_skipped_file_is_not_a_missing_package(tmp_path: Path):
    # tsconfig baseUrl makes `types_db` a local file; collect skips it (too big or binary),
    # but its path still proves the import is local.
    (tmp_path / "tsconfig.json").write_text(json.dumps({"compilerOptions": {"baseUrl": "."}}))
    (tmp_path / "types_db.ts").write_bytes(b"\x00binary")
    (tmp_path / "app.ts").write_text("import type { Database } from 'types_db';\n")
    result = runner.invoke(app, ["audit", str(tmp_path), "--offline", "--format", "json"])
    assert "SC-META-004" not in result.stdout and "SC-DEP-001" not in result.stdout


def hook(payload: Mapping[str, object]) -> object:
    return runner.invoke(app, ["hook", "claude"], input=json.dumps(payload))


def edit(repo: Path, path: str) -> dict[str, object]:
    return {
        "session_id": "s",
        "cwd": str(repo),
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": str(repo / path)},
        "tool_response": {},
    }


def stop(repo: Path) -> dict[str, object]:
    return {
        "session_id": "s",
        "cwd": str(repo),
        "hook_event_name": "Stop",
        "stop_hook_active": False,
    }


def test_hook_after_an_edit_stays_offline(repo: Path):
    package_json(repo, {"react": "^19.0.0", "left-padx": "^1.0.0"})
    result = hook(edit(repo, "package.json"))  # conftest's fetch fails the test if called
    assert result.exit_code == 0, result.output


@pytest.mark.usefixtures("probe")
def test_hook_at_stop_goes_online_for_added_dependencies(
    repo: Path, monkeypatch: pytest.MonkeyPatch
):
    package_json(repo, {"left-padx": "^1.0.0", "react": "^19.0.0"})
    net = use_net(monkeypatch, LEFT_PADX)
    result = hook(stop(repo))
    assert result.exit_code == 0, result.output
    assert net.urls[0] == f"{NPM}/left-padx"


@pytest.mark.parametrize(
    "failure", [FetchError("timed out"), Response(503), Response(429, retry_after="0")]
)
def test_hook_at_stop_survives_any_registry_failure(
    repo: Path, monkeypatch: pytest.MonkeyPatch, failure: Response | Exception
):
    package_json(repo, {"left-padx": "^1.0.0", "react": "^19.0.0"})
    use_net(monkeypatch, {f"{NPM}/left-padx": failure})
    result = hook(stop(repo))
    assert result.exit_code == 0, result.output
