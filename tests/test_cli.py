from typer.testing import CliRunner

from seamscan import __version__
from seamscan.cli import app

runner = CliRunner()


def test_version_flag_works_without_a_command():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_audit_exit_code_reflects_blocking_findings(tmp_path):
    (tmp_path / "client.py").write_text("import requests\nrequests.get(u, verify=False)\n")
    result = runner.invoke(app, ["audit", str(tmp_path)])
    assert result.exit_code == 1
    assert "SC-CODE-001" in result.stdout


def test_audit_clean_directory_exits_zero(tmp_path):
    (tmp_path / "ok.py").write_text("x = 1\n")
    assert runner.invoke(app, ["audit", str(tmp_path)]).exit_code == 0
