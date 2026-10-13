import pytest

from seamscan.model import Confidence, Ecosystem, Finding, Location, PackageRef, Severity
from seamscan.policy.config import Config, ConfigError, DepsPolicy, parse_config
from seamscan.policy.verdict import Policy

KNOWN = frozenset({"SC-CODE-001", "SC-CODE-002", "SC-SUPA-001", "SC-TEST-003"})


def parse(text: str) -> Config:
    return parse_config(text, KNOWN)


def test_empty_file_is_the_default_config():
    config = parse("")
    assert config == Config()
    assert config.policy == Policy()


def test_full_supported_config():
    config = parse(
        """
[policy]
fail_on_severity = "CRITICAL"
fail_on_confidence = "HIGH"
block = "all"

[rules]
disable = ["SC-TEST-003"]
severity = { "SC-CODE-002" = "LOW" }

[paths]
exclude = ["scripts/legacy/**"]
"""
    )
    assert config.policy == Policy(Severity.CRITICAL, Confidence.HIGH, block="all")
    assert config.disabled == frozenset({"SC-TEST-003"})
    assert dict(config.severity) == {"SC-CODE-002": Severity.LOW}
    assert config.exclude == ("scripts/legacy/**",)


@pytest.mark.parametrize(
    ("text", "complaint"),
    [
        ("[policy\n", "invalid TOML"),
        ("[auth]\nprimitives = []\n", "unknown section [auth]"),
        ("[paths]\nclient = ['src/ui/**']\n", "unknown key paths.client"),
        ("[policy]\nfail_on_severty = 'HIGH'\n", "unknown key policy.fail_on_severty"),
        ("policy = 3\n", "[policy] must be a table"),
        ("[policy]\nfail_on_severity = 'HGH'\n", "policy.fail_on_severity"),
        ("[policy]\nfail_on_severity = 3\n", "policy.fail_on_severity"),
        ("[policy]\nfail_on_confidence = 'CRITICAL'\n", "policy.fail_on_confidence"),
        ("[policy]\nblock = 'some'\n", "policy.block must be one of focus, all"),
        ("[policy]\nblock = true\n", "policy.block"),
        ("[rules]\ndisable = 'SC-CODE-001'\n", "rules.disable"),
        ("[rules]\ndisable = ['SC-CODE-999']\n", "rules.disable: unknown rule id 'SC-CODE-999'"),
        ("[rules]\nseverity = 'LOW'\n", "rules.severity"),
        ("[rules]\nseverity = { 'SC-NOPE-1' = 'LOW' }\n", 'rules.severity."SC-NOPE-1"'),
        ("[rules]\nseverity = { 'SC-CODE-001' = 'low' }\n", 'rules.severity."SC-CODE-001"'),
        ("[paths]\nexclude = 'a/**'\n", "paths.exclude"),
        ("[paths]\nexclude = ['/abs/**']\n", "paths.exclude"),
        ("[paths]\nexclude = ['scripts/']\n", "paths.exclude"),
        ("[paths]\nexclude = ['a/b**/c']\n", "paths.exclude"),
        ("[paths]\nexclude = ['']\n", "paths.exclude"),
        ("[deps]\nmin_age = 30\n", "unknown key deps.min_age"),
        ("[deps]\nmin_age_days = '30'\n", "deps.min_age_days"),
        ("[deps]\nmin_age_days = -1\n", "deps.min_age_days"),
        ("[deps]\nmin_age_days = true\n", "deps.min_age_days"),
        ("[deps]\nmin_weekly_downloads = 1.5\n", "deps.min_weekly_downloads"),
        ("[deps]\nallow = '@acme/*'\n", "deps.allow"),
        ("[deps]\nallow = ['']\n", "deps.allow"),
    ],
)
def test_errors_name_the_exact_key(text: str, complaint: str):
    with pytest.raises(ConfigError) as err:
        parse(text)
    assert complaint in str(err.value)


def test_level_error_lists_the_allowed_levels():
    with pytest.raises(ConfigError) as err:
        parse("[policy]\nfail_on_severity = 'HGH'\n")
    assert "LOW, MEDIUM, HIGH, CRITICAL" in str(err.value)


@pytest.mark.parametrize(
    ("pattern", "path", "matches"),
    [
        ("scripts/legacy/**", "scripts/legacy/a.py", True),
        ("scripts/legacy/**", "scripts/legacy/deep/er/a.py", True),
        ("scripts/legacy/**", "scripts/legacy.py", False),
        ("scripts/legacy/**", "other/scripts/legacy/a.py", False),
        ("*.py", "a.py", True),
        ("*.py", "pkg/a.py", False),  # `*` does not cross directories
        ("**/*.py", "a.py", True),  # `**` may match no directories at all
        ("**/*.py", "pkg/sub/a.py", True),
        ("**/*.py", "pkg/a.ts", False),
        ("src/**/test_*.py", "src/test_a.py", True),
        ("src/**/test_*.py", "src/x/y/test_a.py", True),
        ("src/**/test_*.py", "src/x/y/a_test.py", False),
        ("src/*/gen.ts", "src/a/gen.ts", True),
        ("src/*/gen.ts", "src/a/b/gen.ts", False),
        ("a?.py", "ab.py", True),
        ("a?.py", "a/.py", False),
        ("docs/a.b", "docs/aXb", False),  # dots are literal
        ("**", "anything/at/all.py", True),
        ("vendor/lib.py", "vendor/lib.py", True),
        ("vendor", "vendor/lib.py", False),  # whole-path match, not a prefix
    ],
)
def test_exclude_globs(pattern: str, path: str, matches: bool):
    config = parse(f"[paths]\nexclude = [{pattern!r}]\n")
    assert config.excludes(path) is matches


def test_no_excludes_exclude_nothing():
    assert not Config().excludes("a.py")


def finding(rule: str, severity: Severity) -> Finding:
    return Finding(rule, severity, Confidence.HIGH, Location("a.py", 1, 1, 1, 2), "m", "e")


def test_severity_override_wins_over_a_rule_raising_severity_per_finding():
    # SC-SUPA-001 raises itself to CRITICAL when browser code reads the table; the
    # team's explicit choice still applies.
    config = parse("[rules]\nseverity = { 'SC-SUPA-001' = 'MEDIUM' }\n")
    found = config.override_severity(
        [finding("SC-SUPA-001", Severity.CRITICAL), finding("SC-CODE-001", Severity.HIGH)]
    )
    assert [f.severity for f in found] == [Severity.MEDIUM, Severity.HIGH]


def test_deps_defaults_match_the_spec():
    assert Config().deps == DepsPolicy(min_age_days=30, min_weekly_downloads=100, allow=())


def test_deps_section():
    config = parse(
        "[deps]\nmin_age_days = 14\nmin_weekly_downloads = 0\nallow = ['@acme/*', 'acme_*']\n"
    )
    assert config.deps == DepsPolicy(14, 0, ("@acme/*", "acme_*"))


@pytest.mark.parametrize(
    ("ecosystem", "name", "allowed"),
    [
        (Ecosystem.NPM, "@acme/ui", True),
        (Ecosystem.NPM, "@acme/ui/extra", False),  # `*` stays within one segment
        (Ecosystem.NPM, "@acmex/ui", False),
        (Ecosystem.NPM, "acme-core", False),  # npm names compare as written
        (Ecosystem.PYPI, "acme-core", True),  # PyPI names compare normalized
        (Ecosystem.PYPI, "acmecore", False),
    ],
)
def test_deps_allow_globs_match_package_names(ecosystem: Ecosystem, name: str, allowed: bool):
    config = parse("[deps]\nallow = ['@acme/*', 'Acme.*']\n")
    assert config.deps.allows(PackageRef(ecosystem, name)) is allowed
