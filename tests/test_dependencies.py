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


# --- npm manifests ---------------------------------------------------------------------

from seamscan.facts.dependencies import Dependency, registry_dependencies  # noqa: E402


def found(files: dict[str, str]) -> list[tuple[str, str, int]]:
    deps = registry_dependencies([SourceFile(p, t) for p, t in files.items()])
    return [(d.ref.name, d.location.path, d.location.start_line) for d in deps]


def npm(name: str) -> PackageRef:
    return PackageRef(Ecosystem.NPM, name)


def test_npm_optional_and_peer_dependencies_are_declarations_too():
    text = json.dumps(
        {"optionalDependencies": {"fsevents": "^2"}, "peerDependencies": {"react": ">=18"}},
        indent=2,
    )
    assert found({"package.json": text}) == [
        ("fsevents", "package.json", 3),
        ("react", "package.json", 6),
    ]


def test_npm_alias_is_looked_up_under_its_real_name():
    text = json.dumps(
        {"dependencies": {"lodash4": "npm:lodash@^4.17.21", "ui": "npm:@acme/ui@2"}}, indent=2
    )
    deps = registry_dependencies([SourceFile("package.json", text)])
    assert [(d.ref, d.location.start_line) for d in deps] == [
        (npm("lodash"), 3),
        (npm("@acme/ui"), 4),
    ]


def test_npm_local_and_url_specs_are_never_looked_up():
    specs = {
        "a": "file:../a",
        "b": "link:../b",
        "c": "workspace:*",
        "d": "portal:../d",
        "e": "git+https://github.com/x/e.git",
        "f": "github:x/f",
        "g": "x/g#v1",
        "h": "https://example.com/h.tgz",
        "i": "jsr:@std/path@1",
        "j": "../j",
        "k": "catalog:",
        "l": "latest",
    }
    text = json.dumps({"dependencies": specs}, indent=2)
    assert [name for name, _, _ in found({"package.json": text})] == ["k", "l"]


def test_npm_packages_defined_in_the_repository_are_not_looked_up():
    files = {
        "package.json": json.dumps({"name": "root", "workspaces": ["packages/*"]}),
        "packages/ui/package.json": json.dumps({"name": "@acme/ui", "dependencies": {"clsx": "2"}}),
        "apps/web/package.json": json.dumps(
            {"name": "web", "dependencies": {"@acme/ui": "^0.1.0", "next": "16"}}, indent=2
        ),
        "node_modules/x/package.json": json.dumps({"name": "x", "dependencies": {"y": "1"}}),
    }
    assert found(files) == [
        ("next", "apps/web/package.json", 5),
        ("clsx", "packages/ui/package.json", 1),
    ]


def test_npm_only_top_level_sections_count():
    text = json.dumps(
        {"name": "a", "jest": {"dependencies": {"nope": "1"}}, "dependencies": {"react": "19"}},
        indent=2,
    )
    assert found({"package.json": text}) == [("react", "package.json", 9)]


# --- Python manifests ------------------------------------------------------------------


def pypi(name: str) -> PackageRef:
    return PackageRef(Ecosystem.PYPI, name)


def test_requirements_directory_and_direct_references():
    text = (
        "fastapi==0.115.0\n"
        "mylib @ git+https://github.com/acme/mylib\n"
        "other @ file:///opt/other\n"
        "-e .\n"
        "./vendor/pkg\n"
        "uvicorn[standard]>=0.30 ; python_version >= '3.11'\n"
    )
    assert found({"requirements/base.txt": text}) == [
        ("fastapi", "requirements/base.txt", 1),
        ("uvicorn", "requirements/base.txt", 6),
    ]


PYPROJECT = """\
[project]
name = "acme-api"
dependencies = [
    "fastapi[standard]>=0.115",  # "quoted" comment
    # "commented-out>=1",
    "sqlmodel>=0.0.22",
    "pywin32 ; sys_platform == 'win32'",
    "local @ file:///srv/local",
]

[project.optional-dependencies]
dev = ["pytest>=8", "ruff"]

[dependency-groups]
test = [
    {include-group = "lint"},
    "pytest-asyncio>=0.24",
]
lint = ["mypy"]
"""


def test_pyproject_project_tables_with_exact_lines():
    deps = registry_dependencies([SourceFile("pyproject.toml", PYPROJECT)])
    assert [(d.ref.name, d.location.start_line, d.location.start_col) for d in deps] == [
        ("fastapi", 4, 6),
        ("sqlmodel", 6, 6),
        ("pywin32", 7, 6),
        ("pytest", 12, 9),
        ("ruff", 12, 22),
        ("pytest-asyncio", 17, 6),
        ("mypy", 19, 10),
    ]
    assert deps[0].spec == ">=0.115"


def test_pyproject_inline_tables_and_dotted_keys():
    text = (
        'project.name = "x"\n'
        "project.dependencies = ['httpx']\n"
        'project.optional-dependencies = { docs = ["mkdocs"], dev = [\n  "black",\n] }\n'
    )
    assert found({"pyproject.toml": text}) == [
        ("httpx", "pyproject.toml", 2),
        ("mkdocs", "pyproject.toml", 3),
        ("black", "pyproject.toml", 4),
    ]


POETRY = """\
[tool.poetry]
name = "acme"

[tool.poetry.dependencies]
python = "^3.11"
Django = "^5.0"
"zope.interface" = "*"
celery = { version = "^5.4", extras = ["redis"] }
mylib = { path = "../mylib", develop = true }
forked = { git = "https://github.com/acme/forked.git" }

[tool.poetry.group.dev.dependencies]
pytest = "^8"

[tool.poetry.dev-dependencies]
black = "^24"
"""


def test_poetry_tables_skip_python_and_path_or_git_deps():
    assert found({"pyproject.toml": POETRY}) == [
        ("django", "pyproject.toml", 6),
        ("zope-interface", "pyproject.toml", 7),
        ("celery", "pyproject.toml", 8),
        ("pytest", "pyproject.toml", 13),
        ("black", "pyproject.toml", 16),
    ]


def test_uv_sources_and_repository_packages_are_not_looked_up():
    files = {
        "pyproject.toml": (
            "[project]\nname = 'root'\ndependencies = ['shared', 'torch', 'httpx']\n\n"
            "[tool.uv.sources]\ntorch = { index = 'pytorch' }\n"
        ),
        "libs/shared/pyproject.toml": "[project]\nname = 'Shared'\n",
    }
    assert found(files) == [("httpx", "pyproject.toml", 3)]


def test_pipfile_packages():
    text = '[packages]\nrequests = "*"\nlocal = {path = "."}\n\n[dev-packages]\npytest = "*"\n'
    assert found({"Pipfile": text}) == [("requests", "Pipfile", 2), ("pytest", "Pipfile", 6)]


def test_broken_toml_gives_no_dependencies_and_no_crash():
    assert found({"pyproject.toml": "[project\ndependencies = ["}) == []


def test_dependency_records_the_spec_as_written():
    deps = registry_dependencies([SourceFile("Pipfile", '[packages]\nflask = ">=3"\n')])
    assert deps == (Dependency(pypi("flask"), ">=3", deps[0].location),)


def test_toml_strings_comments_and_arrays_of_tables_dont_shift_lines():
    text = (
        "[[tool.poetry.source]]\n"
        'name = "private"\n'
        'url = "https://pypi.acme.dev/simple"\n'
        "\n"
        "[project]\n"
        'description = """\n'
        'dependencies = ["not-a-dep"]\n'
        '"""\n'
        "dependencies = [ # ] a bracket in a comment\n"
        "  'literal-quoted>=1', 'second',\n"
        '  "third[extra]"\n'
        "]\n"
    )
    assert [(n, line) for n, _, line in found({"pyproject.toml": text})] == [
        ("literal-quoted", 10),
        ("second", 10),
        ("third", 11),
    ]


def test_names_that_must_never_reach_a_registry_are_not_checked():
    files = [
        SourceFile(
            "apps/web/package.json",
            json.dumps(
                {
                    "dependencies": {
                        "@acme/ui": "workspace:*",
                        "@acme/db": "^1.0.0",
                        "local-lib": "file:../lib",
                        "forked": "github:acme/forked",
                        "tarball": "https://example.com/t.tgz",
                        "react": "19",
                    }
                }
            ),
        ),
        SourceFile("packages/db/package.json", json.dumps({"name": "@acme/db"})),
        SourceFile("requirements.txt", "internal @ git+https://github.com/acme/internal\nflask\n"),
    ]
    assert dependencies_to_check(files, None) == frozenset({npm("react"), pypi("flask")})


# --- What a change adds -------------------------------------------------------------

from seamscan.facts.dependencies import added_in_change  # noqa: E402

APPENDED = (
    '{\n  "dependencies": {\n    "react": "19",\n    "sharp": "0.33",\n    "zod": "3"\n  }\n}\n'
)


def added(ranges: tuple[tuple[int, int], ...]) -> list[str]:
    files = [SourceFile("package.json", APPENDED)]
    change = ChangeSet(added={"package.json": ranges})
    return [
        d.ref.name for d in declared_dependencies(files) if added_in_change(d, change, APPENDED)
    ]


def test_appending_adds_a_comma_to_the_old_last_entry_but_does_not_add_it():
    assert added(((4, 5),)) == ["zod"]


def test_a_block_inserted_in_the_middle_is_all_new():
    assert added(((3, 4),)) == ["react", "sharp"]


def test_a_single_changed_line_counts_as_added():
    assert added(((4, 4),)) == ["sharp"]


def test_a_new_manifest_is_all_new():
    from seamscan.model import WHOLE_FILE

    assert added((WHOLE_FILE,)) == ["react", "sharp", "zod"]


def test_appending_to_a_toml_array_too():
    text = 'dependencies = [\n    "fastapi",\n    "httpx"\n]\n'
    text = "[project]\n" + text
    files = [SourceFile("pyproject.toml", text)]
    change = ChangeSet(added={"pyproject.toml": ((3, 4),)})
    deps = declared_dependencies(files)
    assert [d.ref.name for d in deps if added_in_change(d, change, text)] == ["httpx"]
