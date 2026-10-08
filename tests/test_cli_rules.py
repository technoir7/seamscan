"""Spec §11.1: `seamscan rules` and `seamscan explain`."""

import json

from typer.testing import CliRunner

from seamscan.cli import app
from seamscan.rules.registry import RULES

runner = CliRunner()


def test_rules_lists_every_registered_rule_sorted():
    result = runner.invoke(app, ["rules"])
    assert result.exit_code == 0
    ids = [line.split()[0] for line in result.stdout.splitlines()[1:]]
    assert ids == sorted(r.meta.id for r in RULES)
    row = next(line for line in result.stdout.splitlines() if line.startswith("SC-CODE-001"))
    assert row.split()[1:3] == ["HIGH", "HIGH"]
    assert "TLS verification disabled" in row
    assert "javascript, python" in row


def test_rules_json_carries_the_metadata():
    result = runner.invoke(app, ["rules", "--json"])
    assert result.exit_code == 0
    rules = json.loads(result.stdout)
    assert [r["id"] for r in rules] == sorted(r.meta.id for r in RULES)
    assert rules[0] == {
        "id": "SC-CODE-001",
        "title": "TLS verification disabled",
        "severity": "HIGH",
        "confidence": "HIGH",
        "languages": ["javascript", "python"],
    }


def test_explain_prints_the_rule_page():
    result = runner.invoke(app, ["explain", "SC-CODE-001"])
    assert result.exit_code == 0
    assert result.stdout.startswith("# SC-CODE-001")
    assert "## How to fix" in result.stdout


def test_explain_accepts_lowercase_ids():
    assert runner.invoke(app, ["explain", "sc-supa-001"]).stdout.startswith("# SC-SUPA-001")


def test_every_rule_has_a_page_explain_can_print():
    for rule in RULES:
        result = runner.invoke(app, ["explain", rule.meta.id])
        assert result.exit_code == 0, rule.meta.id
        assert result.stdout.startswith(f"# {rule.meta.id}"), rule.meta.id


def test_explain_unknown_rule_is_a_usage_error_with_a_hint():
    result = runner.invoke(app, ["explain", "SC-CODE-01"])
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "unknown rule SC-CODE-01" in result.stderr
    assert "seamscan rules" in result.stderr
    assert "SC-CODE-001" in result.stderr  # closest match
