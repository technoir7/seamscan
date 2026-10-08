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


def test_js_file_with_syntax_errors_is_reported():
    findings = analyze([SourceFile("web/app.js", "function (\n")]).findings
    assert [f.rule_id for f in findings] == ["SC-META-002"]


SUPPRESSED = SourceFile(
    "svc/c.py",
    "import requests\n"
    "requests.get(u, verify=False)  # seamscan: ignore[SC-CODE-001] reason: pinned internal CA\n",
)


def test_suppressed_findings_are_listed_with_their_reason():
    a = analyze([*FILES, SUPPRESSED])
    doc = json.loads(render_json(a.findings, decide(a.findings, Policy()), "test", a.suppressed))
    jsonschema.validate(doc, SCHEMA)
    [s] = doc["suppressed"]
    assert (s["rule_id"], s["location"]["path"], s["reason"]) == (
        "SC-CODE-001",
        "svc/c.py",
        "pinned internal CA",
    )
    assert doc["summary"]["suppressed"] == 1
    assert all(f["location"]["path"] != "svc/c.py" for f in doc["findings"])


def test_baselined_findings_are_flagged_and_never_blocking():
    findings = analyze(FILES).findings
    known = frozenset(f.fingerprint for f in findings if f.location.path == "svc/a.py")
    doc = json.loads(render_json(findings, decide(findings, Policy(), known), "test"))
    jsonschema.validate(doc, SCHEMA)
    flagged = {f["location"]["path"]: (f["baselined"], f["blocking"]) for f in doc["findings"]}
    assert flagged["svc/a.py"] == (True, False)
    assert flagged["svc/b.py"] == (False, True)
    assert doc["summary"]["baselined"] == 1
    assert doc["schema_version"] == 1
