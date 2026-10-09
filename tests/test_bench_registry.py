"""Registry fixtures in case.toml (ADR-004: benchmark cases never touch the network)."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from bench.case import CaseError, case_registry, load_case
from seamscan.model import Ecosystem, PackageFacts, PackageRef

HEAD = 'id = "{id}"\ndescription = "d"\nsplit = "dev"\n[provenance]\nsource = "original"\n'
REGISTRY = """
[registry]
now = 2026-10-01T00:00:00Z
min_age_days = 14

[[registry.package]]
ecosystem = "npm"
name = "react-codeshift"
exists = true
first_published = 2026-09-20T00:00:00Z
weekly_downloads = 12
install_scripts = ["postinstall"]

[[registry.package]]
ecosystem = "pypi"
name = "acme-internal"
problem = "offline, and not in the snapshot or the cache"
"""


def write_case(tmp_path: Path, toml: str, files: dict[str, str]) -> Path:
    directory = tmp_path / "c1"
    (directory / "repo").mkdir(parents=True)
    for path, text in files.items():
        (directory / "repo" / path).parent.mkdir(parents=True, exist_ok=True)
        (directory / "repo" / path).write_text(text)
    (directory / "case.toml").write_text(HEAD.format(id="c1") + toml)
    return directory


MANIFESTS = {
    "package.json": json.dumps({"dependencies": {"react-codeshift": "^1.0.0"}}),
    "requirements.txt": "acme-internal==1.0\n",
}


def test_registry_table_becomes_a_registry_view(tmp_path: Path):
    view = case_registry(load_case(write_case(tmp_path, REGISTRY, MANIFESTS)))
    assert view is not None
    assert view.now == datetime(2026, 10, 1, tzinfo=UTC)
    assert view.min_age_days == 14
    assert view.min_weekly_downloads == 100
    assert view.packages == {
        PackageRef(Ecosystem.NPM, "react-codeshift"): PackageFacts(
            exists=True,
            first_published=datetime(2026, 9, 20, tzinfo=UTC),
            weekly_downloads=12,
            install_scripts=("postinstall",),
        ),
        PackageRef(Ecosystem.PYPI, "acme-internal"): PackageFacts(
            exists=None, problem="offline, and not in the snapshot or the cache"
        ),
    }


def test_without_a_registry_table_dependency_rules_are_off(tmp_path: Path):
    assert case_registry(load_case(write_case(tmp_path, "", MANIFESTS))) is None


def test_every_dependency_a_rule_would_look_at_needs_a_fixture(tmp_path: Path):
    files = {**MANIFESTS, "src/app.ts": "import x from 'undeclared-pkg'\n"}
    case = load_case(write_case(tmp_path, REGISTRY, files))
    with pytest.raises(CaseError, match="npm:undeclared-pkg"):
        case_registry(case)


@pytest.mark.parametrize(
    ("fixture", "problem"),
    [
        ('ecosystem = "npm"\nname = "x"\nexists = true\ncolour = "red"', "colour"),
        ('ecosystem = "cargo"\nname = "x"\nexists = true', "ecosystem"),
        ('ecosystem = "pypi"\nname = "Flask_Login"\nexists = true', "flask-login"),
        ('ecosystem = "npm"\nname = "x"', "exists"),
        ('ecosystem = "npm"\nname = "x"\nexists = true\nfirst_published = 2026-01-01', "time"),
    ],
)
def test_bad_fixtures_are_case_errors(tmp_path: Path, fixture: str, problem: str):
    toml = f"[registry]\nnow = 2026-10-01T00:00:00Z\n[[registry.package]]\n{fixture}\n"
    with pytest.raises(CaseError, match=problem):
        load_case(write_case(tmp_path, toml, {}))


def test_now_must_carry_a_timezone(tmp_path: Path):
    with pytest.raises(CaseError, match="now"):
        load_case(write_case(tmp_path, "[registry]\nnow = 2026-10-01T00:00:00\n", {}))


def test_snapshot_lists_popular_packages_compactly(tmp_path: Path):
    toml = (
        '[registry]\nnow = 2026-10-01T00:00:00Z\nsnapshot = ["npm:@types/node", "pypi:fastapi"]\n'
    )
    view = case_registry(load_case(write_case(tmp_path, toml, {})))
    assert view is not None
    assert view.packages == {
        PackageRef(Ecosystem.NPM, "@types/node"): PackageFacts(exists=True, popular=True),
        PackageRef(Ecosystem.PYPI, "fastapi"): PackageFacts(exists=True, popular=True),
    }


def test_a_package_is_either_in_the_snapshot_or_listed(tmp_path: Path):
    toml = (
        '[registry]\nnow = 2026-10-01T00:00:00Z\nsnapshot = ["npm:x"]\n'
        '[[registry.package]]\necosystem = "npm"\nname = "x"\nexists = true\n'
    )
    with pytest.raises(CaseError, match="twice"):
        load_case(write_case(tmp_path, toml, {}))


def test_a_name_the_repo_allow_lists_is_never_looked_up_as_in_the_cli(tmp_path: Path):
    toml = """
[registry]
now = 2026-10-01T00:00:00Z
[[registry.package]]
ecosystem = "pypi"
name = "acme-internal"
exists = false
"""
    files = {
        "requirements.txt": "acme-internal==1.0\n",
        "seamscan.toml": '[deps]\nallow = ["acme-*"]\n',
    }
    view = case_registry(load_case(write_case(tmp_path, toml, files)))
    assert view is not None
    assert PackageRef(Ecosystem.PYPI, "acme-internal") not in view.packages


def test_a_case_config_the_harness_cannot_apply_is_an_error(tmp_path: Path):
    toml = "[registry]\nnow = 2026-10-01T00:00:00Z\n"
    files = {"app.py": "x = 1\n", "seamscan.toml": '[rules]\ndisable = ["SC-CODE-001"]\n'}
    with pytest.raises(CaseError, match="seamscan.toml"):
        case_registry(load_case(write_case(tmp_path, toml, files)))
