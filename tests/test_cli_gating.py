"""seamscan.toml, the baseline and the ratchet, through the CLI (spec §9.3, §9.5)."""

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from seamscan import cli
from seamscan.cli import app
from seamscan.model import Confidence, Severity
from seamscan.rules.base import Rule, meta

runner = CliRunner()

TLS_OFF = "import requests\nrequests.get(u, verify=False)\n"  # SC-CODE-001, blocks
BASELINE = Path(".seamscan") / "baseline.json"


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def audit(root: Path, *args: str):
    return runner.invoke(app, [*args, "audit", str(root)])


def entries(root: Path) -> list[dict[str, str]]:
    return json.loads((root / BASELINE).read_text())["entries"]


# ------------------------------------------------------------------ seamscan.toml


def test_disabled_rule_does_not_run(tmp_path: Path):
    (tmp_path / "client.py").write_text(TLS_OFF)
    (tmp_path / "seamscan.toml").write_text('[rules]\ndisable = ["SC-CODE-001"]\n')
    result = audit(tmp_path)
    assert result.exit_code == 0
    assert "SC-CODE-001" not in result.stdout


def test_severity_override_applies_to_findings_and_the_gate(tmp_path: Path):
    (tmp_path / "client.py").write_text(TLS_OFF)
    (tmp_path / "seamscan.toml").write_text('[rules]\nseverity = { "SC-CODE-001" = "LOW" }\n')
    result = audit(tmp_path)
    assert result.exit_code == 0
    assert "SC-CODE-001  LOW/" in result.stdout


def test_policy_thresholds_feed_the_verdict(tmp_path: Path):
    (tmp_path / "client.py").write_text(TLS_OFF)
    (tmp_path / "seamscan.toml").write_text('[policy]\nfail_on_severity = "CRITICAL"\n')
    assert audit(tmp_path).exit_code == 0


def test_excluded_paths_are_not_analyzed(tmp_path: Path):
    (tmp_path / "legacy").mkdir()
    (tmp_path / "legacy" / "old.py").write_text(TLS_OFF)
    (tmp_path / "client.py").write_text(TLS_OFF)
    (tmp_path / "seamscan.toml").write_text('[paths]\nexclude = ["legacy/**"]\n')
    result = audit(tmp_path)
    assert "client.py" in result.stdout
    assert "legacy/old.py" not in result.stdout


def test_bad_config_is_exit_2_naming_the_file_and_key(tmp_path: Path):
    (tmp_path / "ok.py").write_text("x = 1\n")
    (tmp_path / "seamscan.toml").write_text('[policy]\nfail_on_severty = "HIGH"\n')
    result = audit(tmp_path)
    assert result.exit_code == 2
    assert "seamscan.toml" in result.stderr
    assert "policy.fail_on_severty" in result.stderr


def test_explicit_config_replaces_the_repository_file(tmp_path: Path):
    (tmp_path / "client.py").write_text(TLS_OFF)
    (tmp_path / "seamscan.toml").write_text("[nonsense]\n")  # would be exit 2 if read
    other = tmp_path / "other.toml"
    other.write_text('[rules]\ndisable = ["SC-CODE-001"]\n')
    assert audit(tmp_path, "--config", str(other)).exit_code == 0


def test_missing_explicit_config_is_exit_2(tmp_path: Path):
    (tmp_path / "ok.py").write_text("x = 1\n")
    result = audit(tmp_path, "--config", str(tmp_path / "missing.toml"))
    assert result.exit_code == 2
    assert "missing.toml" in result.stderr


# ------------------------------------------------------------------ baseline


def test_create_writes_the_baseline_and_audit_then_passes(tmp_path: Path):
    (tmp_path / "client.py").write_text(TLS_OFF)
    created = runner.invoke(app, ["baseline", "create", str(tmp_path)])
    assert created.exit_code == 0, created.output
    assert "1 entry" in created.stdout
    assert [(e["rule_id"], e["path"]) for e in entries(tmp_path)] == [("SC-CODE-001", "client.py")]
    result = audit(tmp_path)
    assert result.exit_code == 0
    assert "1 in baseline" in result.stdout


def test_create_is_deterministic(tmp_path: Path):
    (tmp_path / "a.py").write_text(TLS_OFF)
    (tmp_path / "b.py").write_text(TLS_OFF)
    runner.invoke(app, ["baseline", "create", str(tmp_path)])
    first = (tmp_path / BASELINE).read_bytes()
    runner.invoke(app, ["baseline", "create", str(tmp_path)])
    assert (tmp_path / BASELINE).read_bytes() == first


def test_create_overwrites_a_corrupt_baseline(tmp_path: Path):
    (tmp_path / "client.py").write_text(TLS_OFF)
    (tmp_path / ".seamscan").mkdir()
    (tmp_path / BASELINE).write_text("{oops")
    assert runner.invoke(app, ["baseline", "create", str(tmp_path)]).exit_code == 0
    assert len(entries(tmp_path)) == 1


def test_create_refuses_when_a_rule_crashed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def boom(ctx: object) -> list[object]:
        raise RuntimeError("bug")

    crashing = Rule(
        meta("SC-CODE-999", "t", Severity.LOW, Confidence.LOW, (), frozenset(), "s"), boom
    )
    monkeypatch.setattr(cli, "RULES", (crashing,))
    (tmp_path / "ok.py").write_text("x = 1\n")
    result = runner.invoke(app, ["baseline", "create", str(tmp_path)])
    assert result.exit_code == 3
    assert "SC-CODE-999" in result.stderr
    assert not (tmp_path / BASELINE).exists()


def test_corrupt_baseline_is_exit_2_not_ignored(tmp_path: Path):
    (tmp_path / "client.py").write_text(TLS_OFF)
    (tmp_path / ".seamscan").mkdir()
    (tmp_path / BASELINE).write_text('{"version": 1}')
    result = audit(tmp_path)
    assert result.exit_code == 2
    assert "baseline.json" in result.stderr and "entries" in result.stderr


def test_prune_drops_entries_that_match_nothing(tmp_path: Path):
    (tmp_path / "a.py").write_text(TLS_OFF)
    (tmp_path / "b.py").write_text(TLS_OFF)
    runner.invoke(app, ["baseline", "create", str(tmp_path)])
    (tmp_path / "a.py").write_text("x = 1\n")
    result = runner.invoke(app, ["baseline", "prune", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "Removed 1" in result.stdout
    assert [e["path"] for e in entries(tmp_path)] == ["b.py"]


def test_prune_without_a_baseline_is_exit_2(tmp_path: Path):
    (tmp_path / "ok.py").write_text("x = 1\n")
    result = runner.invoke(app, ["baseline", "prune", str(tmp_path)])
    assert result.exit_code == 2
    assert "baseline create" in result.stderr


# ------------------------------------------------------------------ scan mode and the ratchet


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    git(tmp_path, "init", "-q")
    (tmp_path / "ok.py").write_text("x = 1\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "start")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_scan_uses_the_baseline_and_config_at_the_working_directory(repo: Path):
    (repo / "client.py").write_text(TLS_OFF)  # untracked: wholly new to scan
    assert runner.invoke(app, ["scan"]).exit_code == 1
    assert runner.invoke(app, ["baseline", "create"]).exit_code == 0
    result = runner.invoke(app, ["scan"])
    assert result.exit_code == 0, result.output
    assert "1 in baseline" in result.stdout

    (repo / "seamscan.toml").write_text("[nonsense]\n")
    assert runner.invoke(app, ["scan"]).exit_code == 2


def test_ratchet_fails_when_the_baseline_grows_and_passes_when_it_shrinks(repo: Path):
    (repo / "a.py").write_text(TLS_OFF)
    (repo / "b.py").write_text(TLS_OFF)
    runner.invoke(app, ["baseline", "create"])
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "accept existing debt")
    assert runner.invoke(app, ["baseline", "check", "--against", "HEAD"]).exit_code == 0

    (repo / "c.py").write_text(TLS_OFF)
    runner.invoke(app, ["baseline", "create"])
    grew = runner.invoke(app, ["baseline", "check", "--against", "HEAD"])
    assert grew.exit_code == 1
    assert "c.py" in grew.stdout and "SC-CODE-001" in grew.stdout
    assert "a.py" not in grew.stdout

    (repo / "c.py").unlink()
    (repo / "a.py").write_text("x = 1\n")
    runner.invoke(app, ["baseline", "create"])
    assert len(entries(repo)) == 1
    shrank = runner.invoke(app, ["baseline", "check", "--against", "HEAD"])
    assert shrank.exit_code == 0, shrank.output


def test_ratchet_treats_a_baseline_missing_at_the_ref_as_empty(repo: Path):
    (repo / "a.py").write_text(TLS_OFF)
    runner.invoke(app, ["baseline", "create"])
    result = runner.invoke(app, ["baseline", "check", "--against", "HEAD"])
    assert result.exit_code == 1
    assert "a.py" in result.stdout


def test_ratchet_with_no_baseline_anywhere_passes(repo: Path):
    assert runner.invoke(app, ["baseline", "check", "--against", "HEAD"]).exit_code == 0


def test_ratchet_with_an_unknown_ref_is_exit_2(repo: Path):
    result = runner.invoke(app, ["baseline", "check", "--against", "nope"])
    assert result.exit_code == 2
    assert "nope" in result.stderr


def test_ratchet_with_a_corrupt_baseline_at_the_ref_is_exit_2(repo: Path):
    (repo / ".seamscan").mkdir()
    (repo / BASELINE).write_text("[]")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "broken")
    runner.invoke(app, ["baseline", "create"])
    result = runner.invoke(app, ["baseline", "check", "--against", "HEAD"])
    assert result.exit_code == 2
    assert "HEAD" in result.stderr


def test_global_config_does_not_outlive_its_invocation(tmp_path: Path):
    # `_run` is shared by every command (and the hook); a --config from one run must not
    # leak into the next one in the same process.
    (tmp_path / "client.py").write_text(TLS_OFF)
    other = tmp_path / "other.toml"
    other.write_text('[rules]\ndisable = ["SC-CODE-001"]\n')
    assert audit(tmp_path, "--config", str(other)).exit_code == 0
    assert audit(tmp_path).exit_code == 1
