"""SC-SEC rule behavior the benchmark can't see: severity, positions and what gets printed."""

from bench.fake_secrets import FAKES
from seamscan.analysis import analyze
from seamscan.model import Finding, Severity, SourceFile
from seamscan.rules.base import Rule
from seamscan.rules.secrets import ENV_FILE_COMMITTED, PROVIDER_SECRET, RULES, SECRET_FALLBACK

RULE: dict[str, Rule] = {r.meta.id: r for r in RULES}


def run(rule_id: str, files: dict[str, str]) -> tuple[Finding, ...]:
    sources = [SourceFile(path, text) for path, text in files.items()]
    return analyze(sources, rules=[RULE[rule_id]]).findings


def test_live_key_is_critical_and_test_key_is_low():
    live, test = FAKES["FAKE_STRIPE_LIVE"], FAKES["FAKE_STRIPE_TEST"]
    found = run(PROVIDER_SECRET.id, {"app.py": f'LIVE = "{live}"\nTEST = "{test}"\n'})
    assert [(f.location.start_line, f.severity) for f in found] == [
        (1, Severity.CRITICAL),
        (2, Severity.LOW),
    ]


def test_secret_location_points_at_the_secret_inside_a_multiline_string():
    pat = FAKES["FAKE_GITHUB_PAT"]
    src = f'"""Usage.\n\nExample:\n    curl -H "token {pat}" x\n"""\n'
    (f,) = run(PROVIDER_SECRET.id, {"tool.py": src})
    loc = f.location
    assert (loc.start_line, loc.start_col, loc.end_line, loc.end_col) == (4, 20, 4, 20 + len(pat))


def test_secret_location_in_an_env_file():
    key = FAKES["FAKE_OPENAI_PROJ"]
    (f,) = run(PROVIDER_SECRET.id, {".env.example": f'# c\nexport OPENAI_API_KEY="{key}"\n'})
    assert (f.location.path, f.location.start_line, f.location.start_col) == (".env.example", 2, 24)


def test_secret_output_is_redacted():
    key = FAKES["FAKE_ANTHROPIC"]
    found = run(PROVIDER_SECRET.id, {"app.py": f'K = "{key}"\n', ".env": f"K={key}\n"})
    assert len(found) == 2
    for f in found:
        assert key not in f.message and key not in f.evidence
        assert "…" in f.evidence


def test_secrets_in_test_files_and_non_env_files_are_out_of_scope():
    key = FAKES["FAKE_STRIPE_LIVE"]
    files = {
        "tests/test_pay.py": f'K = "{key}"\n',
        ".envrc": f"export K={key}\n",
        "README.md": key,
    }
    assert not run(PROVIDER_SECRET.id, files)


def test_fallback_output_never_shows_the_default():
    src = 'import os\nS = os.environ.get("SESSION_SECRET", "hunter2-prod")\n'
    (f,) = run(SECRET_FALLBACK.id, {"app.py": src})
    assert "SESSION_SECRET" in f.message
    assert "hunter2" not in f.message + f.evidence


def test_fallback_needs_a_secret_word_last_in_the_name():
    src = (
        "import os\n"
        'A = os.getenv("JWT_SECRET_KEY", "x")\n'
        'B = os.getenv("SECRET_KEY_ROTATION_DAYS", "30")\n'
        'C = os.getenv("STRIPE_APIKEY", "x")\n'
        'D = os.getenv("PUBLIC_KEY", "x")\n'
        'E = os.getenv("db_pass", "x")\n'
    )
    assert [f.location.start_line for f in run(SECRET_FALLBACK.id, {"app.py": src})] == [2, 4, 6]


def test_fallback_ignores_non_string_defaults_and_other_lookups():
    src = (
        "import os\n"
        'A = os.getenv("API_TOKEN", 0)\n'
        'B = config.get("API_TOKEN", "x")\n'
        'C = os.environ.get(NAME, "x")\n'
        'D = os.environ.get("API_TOKEN", "   ")\n'
        'E = os.getenv("API_TOKEN", "a") or "b"\n'
    )
    assert [f.location.start_line for f in run(SECRET_FALLBACK.id, {"app.py": src})] == [6]


def test_env_file_output_names_the_key_but_not_the_value():
    (f,) = run(ENV_FILE_COMMITTED.id, {".env": "A=\nDB_PASSWORD=hunter2-prod\nB=x\n"})
    assert f.location.start_line == 2
    assert "DB_PASSWORD" in f.evidence
    assert "hunter2" not in f.message + f.evidence


def test_env_file_names():
    names = [
        ".env",
        "api/.env.local",
        ".env.staging.local",
        ".env.production",
        ".env.development",
        ".env.example",
        ".env.sample",
        ".env.template",
        ".envrc",
    ]
    found = run(ENV_FILE_COMMITTED.id, {n: "DB_PASSWORD=hunter2\n" for n in names})
    assert {f.location.path for f in found} == set(names[:5])


def test_env_file_with_only_public_settings_is_not_reported():
    found = run(ENV_FILE_COMMITTED.id, {".env": "VITE_API_URL=https://api.acme.dev\nPORT=3000\n"})
    assert not found


def test_env_file_reported_at_its_first_sensitive_value():
    text = "NODE_ENV=production\nAPP_NAME=acme\nREDIS_URL=redis://:s3cret@cache:6379/0\n"
    (f,) = run(ENV_FILE_COMMITTED.id, {".env": text})
    assert f.location.start_line == 3
