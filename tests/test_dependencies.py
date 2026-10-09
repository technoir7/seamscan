import json

from seamscan.facts.dependencies import declared_dependencies, dependencies_to_check
from seamscan.model import ChangeSet, Ecosystem, PackageRef, SourceFile


def package_json(deps: dict[str, str], dev: dict[str, str] | None = None) -> str:
    return json.dumps({"name": "app", "dependencies": deps, "devDependencies": dev or {}}, indent=2)


def test_package_json_dependencies_with_their_lines():
    text = package_json({"react": "^19.0.0"}, {"vitest": "^3.0.0"})
    deps = declared_dependencies([SourceFile("web/package.json", text)])
    assert [(d.ref, d.spec, d.location.path, d.location.start_line) for d in deps] == [
        (PackageRef(Ecosystem.NPM, "react"), "^19.0.0", "web/package.json", 4),
        (PackageRef(Ecosystem.NPM, "vitest"), "^3.0.0", "web/package.json", 7),
    ]


def test_requirements_txt_names_are_normalized():
    text = "# deps\nFlask_Login==0.6.3\nrequests>=2  # http\n-r base.txt\n\n"
    deps = declared_dependencies([SourceFile("requirements.txt", text)])
    assert [(d.ref.name, d.spec, d.location.start_line) for d in deps] == [
        ("flask-login", "==0.6.3", 2),
        ("requests", ">=2", 3),
    ]
    assert {d.ref.ecosystem for d in deps} == {Ecosystem.PYPI}


def test_scan_mode_checks_only_dependencies_on_added_lines():
    text = package_json({"react": "^19.0.0", "left-padx": "1.0.0"})
    files = [SourceFile("package.json", text)]
    change = ChangeSet(added={"package.json": ((5, 5),)})
    assert dependencies_to_check(files, change) == frozenset(
        {PackageRef(Ecosystem.NPM, "left-padx")}
    )
    assert len(dependencies_to_check(files, None)) == 2


def test_registry_view_reaches_the_rules():
    from datetime import UTC, datetime

    from seamscan.analysis import analyze
    from seamscan.model import Confidence, Finding, RegistryView, Severity
    from seamscan.rules.base import Rule, RuleContext, meta

    seen: list[RegistryView | None] = []

    def probe(ctx: RuleContext) -> list[Finding]:
        seen.append(ctx.registry)
        return []

    rule = Rule(
        meta("SC-META-999", "probe", Severity.LOW, Confidence.LOW, (), frozenset(), ""), probe
    )
    view = RegistryView(packages={}, now=datetime(2026, 10, 1, tzinfo=UTC))
    analyze([], rules=[rule], registry=view)
    analyze([], rules=[rule])
    assert seen == [view, None]
