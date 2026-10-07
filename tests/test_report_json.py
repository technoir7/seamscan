"""Spec §5.1 determinism and §10 JSON schema."""

import json
import random
from pathlib import Path

import jsonschema

from seamscan.analysis import analyze
from seamscan.model import SourceFile
from seamscan.policy.verdict import Policy, decide
from seamscan.report.json import render_json

SCHEMA = json.loads(
    (Path(__file__).resolve().parent.parent / "schemas" / "findings.v1.schema.json").read_text()
)

FILES = [
    SourceFile("svc/a.py", "import requests\nrequests.get(u, verify=False)\n"),
    SourceFile("svc/b.py", "import httpx\nc = httpx.Client(verify=False)\n"),
    SourceFile("svc/broken.py", "def (:\n"),
    SourceFile("svc/clean.py", "x = 1\n"),
]


def render(files: list[SourceFile]) -> str:
    findings = analyze(files).findings
    return render_json(findings, decide(findings, Policy()), tool_version="test")


def test_output_is_byte_identical_regardless_of_input_order():
    shuffled = FILES[:]
    random.Random(7).shuffle(shuffled)
    assert render(FILES) == render(shuffled)


def test_output_matches_schema():
    jsonschema.validate(json.loads(render(FILES)), SCHEMA)


def test_parse_failure_is_reported_not_skipped():
    rules = [f["rule_id"] for f in json.loads(render(FILES))["findings"]]
    assert "SC-META-002" in rules
