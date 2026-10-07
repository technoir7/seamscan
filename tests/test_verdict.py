"""The terminal verdict, verdict.md and the exit code must come from one decision."""

import shutil
from pathlib import Path

import pytest

from clogbot.legacy import (
    CheckResult,
    HeuristicWarning,
    Severity,
    compute_verdict,
    generate_verdict_md,
    validate_node_imports,
)


def failed_import_check() -> CheckResult:
    return CheckResult(
        name="Python Import Validation (totally_real_helpers)",
        passed=False,
        severity=Severity.SUSPICIOUS_IMPORT,
        error_message="Suspicious import: 'totally_real_helpers' cannot be resolved",
    )


def test_failed_import_check_blocks():
    verdict = compute_verdict([failed_import_check()], [], fail_on_warn=False)
    assert verdict.exit_code == 1
    assert verdict.blocking


def test_warnings_alone_do_not_block_by_default():
    warnings = [HeuristicWarning(message="[CLASS-12] TLS verification bypass")]
    verdict = compute_verdict([], warnings, fail_on_warn=False)
    assert verdict.exit_code == 0
    assert not verdict.blocking


def test_warnings_block_with_fail_on_warn():
    warnings = [HeuristicWarning(message="[CLASS-12] TLS verification bypass")]
    verdict = compute_verdict([], warnings, fail_on_warn=True)
    assert verdict.exit_code == 2


def test_verdict_md_heading_matches_non_blocking_verdict(tmp_path: Path):
    warnings = [HeuristicWarning(message="[CLASS-12] TLS verification bypass")]
    verdict = compute_verdict([], warnings, fail_on_warn=False)
    generate_verdict_md([], warnings, verdict, tmp_path)
    text = (tmp_path / "verdict.md").read_text()
    assert "Failures Detected" not in text
    assert verdict.headline in text


def test_verdict_md_heading_matches_blocking_verdict(tmp_path: Path):
    verdict = compute_verdict([failed_import_check()], [], fail_on_warn=False)
    generate_verdict_md([failed_import_check()], [], verdict, tmp_path)
    assert verdict.headline in (tmp_path / "verdict.md").read_text()


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_node_import_name_cannot_inject_code(tmp_path: Path):
    marker = tmp_path / "PWNED"
    hostile = f"x');require('fs').writeFileSync('{marker}','1');('"
    validate_node_imports([hostile], tmp_path)
    assert not marker.exists()
