import json
import subprocess
from pathlib import Path

import jsonschema
from typer.testing import CliRunner

from seamscan import __version__
from seamscan.cli import app
from seamscan.rules.registry import ALL_META

runner = CliRunner()


def test_version_flag_works_without_a_command():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


FALLBACK_SECRET = 'import os\nSECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")\n'


def test_audit_exit_code_reflects_blocking_findings(tmp_path):
    (tmp_path / "settings.py").write_text(FALLBACK_SECRET)
    result = runner.invoke(app, ["audit", str(tmp_path)])
    assert result.exit_code == 1
    assert "SC-SEC-003" in result.stdout


def test_a_hint_is_reported_without_failing_the_run(tmp_path):
    # ADR-006: outside the focus checks (Supabase, Firebase, secrets) findings are hints.
    (tmp_path / "client.py").write_text("import requests\nrequests.get(u, verify=False)\n")
    result = runner.invoke(app, ["audit", str(tmp_path)])
    assert result.exit_code == 0
    assert "SC-CODE-001" in result.stdout
    (tmp_path / "seamscan.toml").write_text('[policy]\nblock = "all"\n')
    assert runner.invoke(app, ["audit", str(tmp_path)]).exit_code == 1


def test_audit_clean_directory_exits_zero(tmp_path):
    (tmp_path / "ok.py").write_text("x = 1\n")
    assert runner.invoke(app, ["audit", str(tmp_path)]).exit_code == 0


# --- Output formats and --stats (spec §10, §11.1) ---

FIXTURES = Path(__file__).parent / "fixtures"
SARIF_SCHEMA = json.loads((FIXTURES / "sarif" / "sarif-schema-2.1.0.json").read_text())
VERIFY_OFF = "import requests\nrequests.get(u, verify=False)\n"


def repo(tmp_path: Path) -> Path:
    (tmp_path / "client.py").write_text(VERIFY_OFF)
    (tmp_path / "settings.py").write_text(FALLBACK_SECRET)  # blocks: a focus check
    (tmp_path / "broken.py").write_text("def (:\n")
    (tmp_path / "noreason.py").write_text(
        "import requests\nrequests.get(u, verify=False)  # seamscan: ignore[SC-CODE-001]\n"
    )
    (tmp_path / "ok.py").write_text(
        "import requests\n"
        "requests.get(u, verify=False)  # seamscan: ignore[SC-CODE-001] reason: test server\n"
    )
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\0\0")
    return tmp_path


def test_sarif_output_is_valid_and_describes_every_rule_it_uses(tmp_path):
    result = runner.invoke(app, ["audit", str(repo(tmp_path)), "--format", "sarif"])
    assert result.exit_code == 1
    doc = json.loads(result.stdout)
    jsonschema.Draft4Validator(SARIF_SCHEMA).validate(doc)
    run = doc["runs"][0]
    described = {r["id"] for r in run["tool"]["driver"]["rules"]}
    assert described == {m.id for m in ALL_META}
    assert {"SC-META-001", "SC-META-002", "SC-META-003"} <= described
    used = {r["ruleId"] for r in run["results"]}
    assert {"SC-CODE-001", "SC-META-001", "SC-META-002"} <= used <= described


def test_markdown_report_from_the_cli(tmp_path):
    result = runner.invoke(app, ["audit", str(repo(tmp_path)), "--format", "md"])
    assert result.exit_code == 1
    assert result.stdout.startswith("# ")
    assert "## 6. Method and limits" in result.stdout
    assert "| `ok.py` line 2 | test server |" in result.stdout
    assert "`logo.png`" in result.stdout


def test_stats_go_to_stderr_so_stdout_stays_machine_readable(tmp_path):
    result = runner.invoke(app, ["audit", str(repo(tmp_path)), "--format", "json", "--stats"])
    doc = json.loads(result.stdout)
    assert doc["suppressed"][0]["reason"] == "test server"
    assert "seamscan stats" in result.stderr
    assert "    logo.png: binary\n" in result.stderr
    assert "    ok.py:2 SC-CODE-001: test server\n" in result.stderr


def test_terminal_mentions_suppressions_in_one_line(tmp_path):
    result = runner.invoke(app, ["audit", str(repo(tmp_path))])
    assert "seamscan: 1 suppressed inline (see --stats)" in result.stdout
    assert result.stderr == ""


def git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def test_scan_supports_sarif_and_stats(tmp_path, monkeypatch):
    git(tmp_path, "init", "-q")
    (tmp_path / "old.py").write_text(VERIFY_OFF)
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "base")
    (tmp_path / "new.py").write_text(VERIFY_OFF)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["scan", "--format", "sarif", "--stats"])
    assert result.exit_code == 0  # TLS off is a hint (ADR-006): in the SARIF, not the exit code
    doc = json.loads(result.stdout)
    jsonschema.Draft4Validator(SARIF_SCHEMA).validate(doc)
    uris = [
        r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
        for r in doc["runs"][0]["results"]
    ]
    assert uris == ["new.py"]
    assert "  files analyzed: 1\n" in result.stderr
