"""Unit tests for Stage 1 taxonomy additions: CLASS-12, CLASS-13, CLASS-14."""

from pathlib import Path

from seamscan.legacy import (
    GitDiffMeta,
    _detect_fallback_secrets,
    _detect_new_dependency_risk,
    _detect_tls_bypass,
)


def make_diff(file_path: str, added_lines, removed_lines=None):
    """Build a minimal synthetic unified diff for a single file."""
    removed_lines = removed_lines or []
    body = [
        f"diff --git a/{file_path} b/{file_path}",
        "index 0000000..1111111 100644",
        f"--- a/{file_path}",
        f"+++ b/{file_path}",
        "@@ -1,3 +1,3 @@",
    ]
    for line in removed_lines:
        body.append(f"-{line}")
    for line in added_lines:
        body.append(f"+{line}")
    return "\n".join(body) + "\n"


def make_multi_file_diff(chunks):
    """chunks: list of (file_path, added_lines) tuples."""
    return "\n".join(make_diff(fp, lines) for fp, lines in chunks)


# =============================================================================
# CLASS-12: TLS/Certificate Verification Bypass
# =============================================================================


def test_tls_bypass_reject_unauthorized_false_positive():
    diff_content = make_diff("src/db.js", ["const opts = { rejectUnauthorized: false };"])
    warnings = _detect_tls_bypass(diff_content, GitDiffMeta())
    assert any(
        "[CLASS-12]" in w.message and "rejectUnauthorized: false" in w.message for w in warnings
    )


def test_tls_bypass_reject_unauthorized_true_negative():
    diff_content = make_diff("src/db.js", ["const opts = { rejectUnauthorized: true };"])
    warnings = _detect_tls_bypass(diff_content, GitDiffMeta())
    assert not any("[CLASS-12]" in w.message for w in warnings)


def test_tls_bypass_python_verify_false():
    diff_content = make_diff("src/client.py", ["requests.get(url, verify=False)"])
    warnings = _detect_tls_bypass(diff_content, GitDiffMeta())
    assert any("[CLASS-12]" in w.message and "verify=False" in w.message for w in warnings)


def test_tls_bypass_duplication_booster_fires_across_two_files():
    diff_content = make_multi_file_diff(
        [
            ("src/db.js", ["const opts = { rejectUnauthorized: false };"]),
            ("deploy/migrate.js", ["const opts = { rejectUnauthorized: false };"]),
        ]
    )
    warnings = _detect_tls_bypass(diff_content, GitDiffMeta())
    assert any("duplicated across 2 files" in w.message for w in warnings)


def test_tls_bypass_duplication_booster_does_not_fire_for_single_file():
    diff_content = make_diff("src/db.js", ["const opts = { rejectUnauthorized: false };"])
    warnings = _detect_tls_bypass(diff_content, GitDiffMeta())
    assert not any("duplicated across" in w.message for w in warnings)


def test_tls_bypass_sequelize_pattern_does_not_bleed_across_files():
    # File A is SAFE (rejectUnauthorized: true) and just happens to mention
    # dialectOptions/ssl. File B is unrelated and has its own, non-Sequelize
    # rejectUnauthorized: false. The Sequelize DOTALL pattern must not stitch
    # these together across the `diff --git` file boundary.
    diff_content = make_multi_file_diff(
        [
            (
                "src/db.js",
                ["const dialectOptions = { ssl: { rejectUnauthorized: true } };"],
            ),
            (
                "src/unrelated_websocket_client.js",
                ["const wsOpts = { rejectUnauthorized: false };"],
            ),
        ]
    )
    warnings = _detect_tls_bypass(diff_content, GitDiffMeta())
    assert not any("Sequelize" in w.message for w in warnings)


def test_tls_bypass_sequelize_pattern_fires_within_single_file():
    diff_content = make_diff(
        "src/db.js",
        ["const dialectOptions = { ssl: { rejectUnauthorized: false } };"],
    )
    warnings = _detect_tls_bypass(diff_content, GitDiffMeta())
    assert any("Sequelize" in w.message for w in warnings)


def test_tls_bypass_reject_unauthorized_false_fires_exactly_once():
    diff_content = make_diff("src/db.js", ["const opts = { rejectUnauthorized: false };"])
    warnings = _detect_tls_bypass(diff_content, GitDiffMeta())
    class_12_warnings = [w for w in warnings if "[CLASS-12]" in w.message]
    assert len(class_12_warnings) == 1


def test_tls_bypass_reject_unauthorized_variable_still_detected():
    diff_content = make_diff("src/db.js", ["const opts = { rejectUnauthorized: someVariable };"])
    warnings = _detect_tls_bypass(diff_content, GitDiffMeta())
    assert any("non-literal-true value" in w.message for w in warnings)


# =============================================================================
# CLASS-13: Insecure Fallback Secret
# =============================================================================


def test_fallback_secret_js_or_operator_positive():
    diff_content = make_diff(
        "src/config.js",
        ["const secret = process.env.SESSION_SECRET || 'dev-secret-placeholder';"],
    )
    warnings = _detect_fallback_secrets(diff_content)
    assert any("[CLASS-13]" in w.message and "SESSION_SECRET" in w.message for w in warnings)


def test_fallback_secret_no_fallback_negative():
    diff_content = make_diff("src/config.js", ["const secret = process.env.SESSION_SECRET;"])
    warnings = _detect_fallback_secrets(diff_content)
    assert not any("[CLASS-13]" in w.message for w in warnings)


def test_fallback_secret_python_getenv_positive():
    diff_content = make_diff(
        "app/settings.py",
        ["API_KEY = os.getenv('API_KEY', 'dev-key-placeholder')"],
    )
    warnings = _detect_fallback_secrets(diff_content)
    assert any("[CLASS-13]" in w.message and "API_KEY" in w.message for w in warnings)


def test_fallback_secret_exclude_literal_empty_string():
    diff_content = make_diff("src/config.js", ["const secret = process.env.SECRET || '';"])
    warnings = _detect_fallback_secrets(diff_content)
    assert not any("[CLASS-13]" in w.message for w in warnings)


def test_fallback_secret_exclude_literal_changeme():
    diff_content = make_diff(
        "app/settings.py",
        ["DB_PASSWORD = os.environ.get('DB_PASSWORD', 'changeme')"],
    )
    warnings = _detect_fallback_secrets(diff_content)
    assert not any("[CLASS-13]" in w.message for w in warnings)


def test_fallback_secret_or_pattern_exclude_literal_changeme():
    diff_content = make_diff(
        "app/settings.py",
        ["DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'changeme'"],
    )
    warnings = _detect_fallback_secrets(diff_content)
    assert not any("[CLASS-13]" in w.message for w in warnings)


def test_fallback_secret_or_pattern_still_detects_real_default():
    diff_content = make_diff(
        "app/settings.py",
        ["DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'a-real-looking-default-abc123'"],
    )
    warnings = _detect_fallback_secrets(diff_content)
    assert any("[CLASS-13]" in w.message and "DB_PASSWORD" in w.message for w in warnings)


# =============================================================================
# CLASS-14: Slopsquatting / Newly-Added Dependency Risk
# =============================================================================


def test_new_dependency_npm_positive():
    diff_content = make_diff(
        "package.json",
        ['"left-pad-plus": "^1.0.0",'],
        removed_lines=[],
    )
    warnings = _detect_new_dependency_risk(diff_content, GitDiffMeta(), Path("."))
    assert any("[CLASS-14]" in w.message and "left-pad-plus" in w.message for w in warnings)


def test_new_dependency_npm_version_bump_negative():
    diff_content = make_diff(
        "package.json",
        added_lines=['"lodash": "^4.17.21",'],
        removed_lines=['"lodash": "^4.17.20",'],
    )
    warnings = _detect_new_dependency_risk(diff_content, GitDiffMeta(), Path("."))
    assert not any("lodash" in w.message for w in warnings)


def test_new_dependency_pip_positive():
    diff_content = make_diff(
        "requirements.txt",
        added_lines=["sus-package==1.0.0"],
    )
    warnings = _detect_new_dependency_risk(diff_content, GitDiffMeta(), Path("."))
    assert any("[CLASS-14]" in w.message and "sus-package" in w.message for w in warnings)


def test_new_dependency_ignores_unrelated_files():
    diff_content = make_diff(
        "src/index.js",
        added_lines=['"totally-new-thing": "^1.0.0",'],
    )
    warnings = _detect_new_dependency_risk(diff_content, GitDiffMeta(), Path("."))
    assert not any("[CLASS-14]" in w.message for w in warnings)
