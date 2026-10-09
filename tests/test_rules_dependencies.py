"""SC-DEP-001..003 and SC-META-004 over plain registry data (spec §7.7, ADR-004)."""

import json
from datetime import UTC, datetime, timedelta

from seamscan.analysis import analyze
from seamscan.model import (
    ChangeSet,
    Ecosystem,
    Finding,
    PackageFacts,
    PackageRef,
    RegistryView,
    SourceFile,
)

NOW = datetime(2026, 10, 1, tzinfo=UTC)
OLD = datetime(2019, 1, 1, tzinfo=UTC)


def manifest(**deps: str) -> SourceFile:
    return SourceFile("package.json", json.dumps({"name": "app", "dependencies": deps}, indent=2))


def view(facts: dict[str, PackageFacts], **limits: int) -> RegistryView:
    packages = {
        PackageRef(Ecosystem(key.split(":")[0]), key.split(":", 1)[1]): f
        for key, f in facts.items()
    }
    return RegistryView(packages, NOW, **limits)


def dep_findings(
    files: list[SourceFile],
    registry: RegistryView | None,
    change: ChangeSet | None = None,
    context: list[SourceFile] | None = None,
) -> list[Finding]:
    result = analyze(files, change=change, registry=registry, context=context or [])
    return [f for f in result.findings if f.rule_id.startswith(("SC-DEP", "SC-META-004"))]


def ids(findings: list[Finding]) -> list[tuple[str, int]]:
    return [(f.rule_id, f.location.start_line) for f in findings]


MISSING = PackageFacts(exists=False)


def test_no_registry_view_means_no_dependency_findings():
    assert dep_findings([manifest(**{"left-padx": "1.0.0"})], None) == []


def test_a_dependency_with_no_facts_is_not_reported():
    # Not looked up: skipped as private, allowed by config, or not in this change.
    assert dep_findings([manifest(**{"left-padx": "1.0.0"})], view({})) == []


def test_missing_package_is_reported_where_it_is_declared():
    found = dep_findings(
        [manifest(react="19", **{"left-padx": "1.0.0"})], view({"npm:left-padx": MISSING})
    )
    assert ids(found) == [("SC-DEP-001", 5)]
    assert "npm has no package named left-padx" in found[0].message
    assert "invent" in found[0].message
    assert found[0].location.start_col == 6


def test_missing_python_package_names_pypi():
    files = [SourceFile("requirements.txt", "flask==3.1.0\nflask-jwt-guard==0.4\n")]
    found = dep_findings(files, view({"pypi:flask-jwt-guard": MISSING}))
    assert ids(found) == [("SC-DEP-001", 2)]
    assert "PyPI has no package named flask-jwt-guard" in found[0].message


def test_missing_import_says_it_is_declared_nowhere():
    files = [manifest(react="19"), SourceFile("src/a.ts", "import x from 'made-up-sdk/client'\n")]
    found = dep_findings(files, view({"npm:made-up-sdk": MISSING}))
    assert ids(found) == [("SC-DEP-001", 1)]
    assert found[0].location.path == "src/a.ts"
    assert "no package.json declares it" in found[0].message


def test_unverified_is_never_missing():
    unknown = PackageFacts(exists=None, problem="npm did not answer within 10 s")
    found = dep_findings([manifest(**{"left-padx": "1.0.0"})], view({"npm:left-padx": unknown}))
    assert ids(found) == [("SC-META-004", 4)]
    assert "npm did not answer within 10 s" in found[0].message


def test_too_new_and_too_obscure():
    files = [manifest(young="1", obscure="1", fine="1", edge="1")]
    facts = {
        "npm:young": PackageFacts(True, NOW - timedelta(days=6), 50_000),
        "npm:obscure": PackageFacts(True, OLD, 12),
        "npm:fine": PackageFacts(True, OLD, 5_000),
        "npm:edge": PackageFacts(True, NOW - timedelta(days=30), 100),
    }
    found = dep_findings(files, view(facts))
    assert ids(found) == [("SC-DEP-002", 4), ("SC-DEP-002", 5)]
    assert found[0].message.startswith("young was first published 6 days ago (")
    assert found[1].message.startswith("obscure had 12 downloads last week (")


def test_thresholds_come_from_the_view():
    files = [manifest(young="1")]
    facts = {"npm:young": PackageFacts(True, NOW - timedelta(days=10), 5)}
    assert dep_findings(files, view(facts, min_age_days=7, min_weekly_downloads=5)) == []


def test_pypi_downloads_are_not_a_signal():
    files = [SourceFile("requirements.txt", "niche==1.0\n")]
    facts = {"pypi:niche": PackageFacts(True, OLD, weekly_downloads=3)}
    assert dep_findings(files, view(facts)) == []


def test_a_snapshot_hit_is_never_too_new():
    hit = PackageFacts(True, popular=True)
    assert dep_findings([manifest(react="19")], view({"npm:react": hit})) == []
    # Even if some age data came along with it.
    young = PackageFacts(True, NOW - timedelta(days=1), 5, popular=True)
    assert dep_findings([manifest(react="19")], view({"npm:react": young})) == []


def test_missing_age_or_download_data_is_not_a_finding():
    facts = {"npm:x": PackageFacts(True)}  # e.g. a failed refresh
    assert dep_findings([manifest(x="1")], view(facts)) == []


SCRIPTS = PackageFacts(True, OLD, 10_000, install_scripts=("postinstall", "prepare", "install"))


def test_install_scripts_on_a_dependency_added_in_this_change():
    files = [manifest(react="19", sharp="0.33")]
    change = ChangeSet(added={"package.json": ((5, 5),)})
    found = dep_findings(files, view({"npm:sharp": SCRIPTS, "npm:react": SCRIPTS}), change)
    assert ids(found) == [("SC-DEP-003", 5)]
    assert "install, postinstall" in found[0].message
    assert "prepare" not in found[0].message


def test_appending_after_an_old_dependency_does_not_make_it_new():
    # Appending "zod" adds a comma to the old last entry, so a diff reports that line too.
    files = [manifest(react="19", sharp="0.33", zod="3")]
    change = ChangeSet(added={"package.json": ((5, 6),)})
    facts = {"npm:sharp": SCRIPTS, "npm:zod": PackageFacts(True, OLD, 10_000, ())}
    assert dep_findings(files, view(facts), change) == []


def test_unknown_install_scripts_are_not_a_finding():
    files = [manifest(sharp="0.33")]
    change = ChangeSet(added={"package.json": ((4, 4),)})
    assert dep_findings(files, view({"npm:sharp": PackageFacts(True, popular=True)}), change) == []


def test_install_scripts_are_old_news_in_an_audit():
    assert dep_findings([manifest(sharp="0.33")], view({"npm:sharp": SCRIPTS})) == []


def test_an_import_is_not_an_install():
    files = [manifest(react="19"), SourceFile("build.ts", "import { build } from 'esbuild'\n")]
    change = ChangeSet(added={"build.ts": ((1, 1),)})
    assert dep_findings(files, view({"npm:esbuild": SCRIPTS}), change) == []


def test_scan_mode_sees_manifests_that_only_arrive_as_context():
    # The CLI's scan passes the changed files and the rest of the repo as context: an
    # import in a changed file is still declared by an unchanged package.json.
    source = SourceFile("src/a.ts", "import x from 'declared-pkg'\nimport y from 'gone-pkg'\n")
    change = ChangeSet(added={"src/a.ts": ((1, 2),)})
    facts = {"npm:declared-pkg": MISSING, "npm:gone-pkg": MISSING}
    found = dep_findings(
        [source], view(facts), change, context=[manifest(**{"declared-pkg": "1"}), source]
    )
    assert ids(found) == [("SC-DEP-001", 2)]
