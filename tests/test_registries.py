"""Which registries a repository uses, read from its config files (ADR-004). Pure."""

from seamscan.facts.registries import registry_config
from seamscan.model import Ecosystem, PackageRef, SourceFile


def npm(name: str) -> PackageRef:
    return PackageRef(Ecosystem.NPM, name)


def pypi(name: str) -> PackageRef:
    return PackageRef(Ecosystem.PYPI, name)


def test_no_config_files_means_the_public_registries_only():
    config = registry_config([SourceFile("app.py", "x = 1\n")])
    assert config.other_registries == frozenset()
    assert not config.is_private(npm("@acme/ui"))


def test_npmrc_scope_mapping_makes_the_scope_private():
    npmrc = (
        "# company packages\n"
        "@acme:registry=https://npm.acme.internal/\n"
        "//npm.acme.internal/:_authToken=${NPM_TOKEN}\n"
        "save-exact=true\n"
    )
    config = registry_config([SourceFile(".npmrc", npmrc)])
    assert config.is_private(npm("@acme/ui"))
    assert not config.is_private(npm("@acmex/ui"))
    assert not config.is_private(npm("react"))
    # A scope mapping alone doesn't change where unscoped names come from.
    assert config.other_registries == frozenset()


def test_npmrc_default_registry_elsewhere_makes_a_404_inconclusive():
    config = registry_config([SourceFile("web/.npmrc", "registry = https://npm.acme.internal/\n")])
    assert config.other_registries == frozenset({Ecosystem.NPM})
    assert not config.is_private(npm("react"))  # still looked up; only a 404 changes meaning


def test_npmrc_naming_the_public_registry_is_not_another_registry():
    npmrc = "registry=https://registry.npmjs.org/\n@acme:registry=https://registry.npmjs.org\n"
    config = registry_config([SourceFile(".npmrc", npmrc)])
    assert config.other_registries == frozenset()
    assert not config.is_private(npm("@acme/ui"))


def test_requirements_index_options_point_pypi_elsewhere():
    for line in (
        "--index-url https://pypi.acme.internal/simple",
        "-i https://pypi.acme.internal/simple",
        "--extra-index-url=https://pypi.acme.internal/simple",
    ):
        text = f"{line}\nrequests==2.32.0\n"
        config = registry_config([SourceFile("requirements/base.txt", text)])
        assert config.other_registries == frozenset({Ecosystem.PYPI}), line


def test_requirements_index_url_at_pypi_is_the_public_registry():
    text = "--index-url https://pypi.org/simple\nrequests\n"
    assert registry_config([SourceFile("requirements.txt", text)]).other_registries == frozenset()


def test_pyproject_uv_index_and_poetry_source():
    uv = '[project]\nname = "app"\n\n[[tool.uv.index]]\nname = "acme"\nurl = "https://pypi.acme.internal/simple"\n'
    poetry = '[[tool.poetry.source]]\nname = "acme"\nurl = "https://pypi.acme.internal/simple"\n'
    for text in (uv, poetry):
        config = registry_config([SourceFile("pyproject.toml", text)])
        assert config.other_registries == frozenset({Ecosystem.PYPI})


def test_pyproject_uv_sources_are_never_looked_up():
    text = (
        '[tool.uv.sources]\nAcme_Core = { index = "acme" }\nlocal-lib = { path = "../lib" }\n'
        '[[tool.uv.index]]\nname = "acme"\nurl = "https://pypi.acme.internal/simple"\n'
        "explicit = true\n"
    )
    config = registry_config([SourceFile("pyproject.toml", text)])
    assert config.is_private(pypi("acme-core"))
    assert config.is_private(pypi("local-lib"))
    assert not config.is_private(pypi("requests"))


def test_unreadable_pyproject_is_not_an_error_here():
    # ProjectModel reports broken manifests; this module just learns nothing from them.
    config = registry_config([SourceFile("pyproject.toml", "[[tool.uv.index]\n")])
    assert config.other_registries == frozenset()


def test_poetry_dependencies_pinned_to_a_source_are_private():
    text = (
        "[tool.poetry.dependencies]\n"
        'python = "^3.12"\n'
        'acme-core = { version = "^1.0", source = "acme" }\n'
        "[tool.poetry.group.dev.dependencies]\n"
        'acme_testkit = { version = "*", source = "acme" }\n'
        'pytest = "^8"\n'
    )
    config = registry_config([SourceFile("pyproject.toml", text)])
    assert config.is_private(pypi("acme-core"))
    assert config.is_private(pypi("acme-testkit"))
    assert not config.is_private(pypi("pytest"))
