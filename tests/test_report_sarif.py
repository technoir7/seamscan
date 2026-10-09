"""Spec §10 SARIF 2.1.0 for GitHub code scanning, validated against the OASIS schema."""

import json
import random
from dataclasses import replace
from pathlib import Path

import jsonschema
import pytest

from seamscan.analysis import Analysis, analyze
from seamscan.model import Confidence, Finding, Location, Severity, SourceFile
from seamscan.policy.verdict import Policy, decide
from seamscan.report.sarif import MAX_RESULTS, render_sarif
from seamscan.rules.registry import ALL_META

SCHEMA = json.loads(
    (Path(__file__).parent / "fixtures" / "sarif" / "sarif-schema-2.1.0.json").read_text()
)

VITE = SourceFile("package.json", '{"devDependencies": {"vite": "7"}}')
MIGRATION = SourceFile(
    "supabase/migrations/1_init.sql", "create table public.messages (id int, body text);\n"
)
CLIENT = SourceFile(
    "src/components/Chat.tsx",
    "import { supabase } from '../lib/supabase';\n"
    "export const load = () => supabase.from('messages').select('*');\n",
)
FILES = [
    VITE,
    MIGRATION,
    CLIENT,
    SourceFile("svc/a.py", "import requests\nrequests.get(u, verify=False)\n"),
    SourceFile("svc/b.py", "import httpx\nc = httpx.Client(verify=False)\n"),
    SourceFile("svc/my file.py", "def (:\n"),
    SourceFile(
        "svc/c.py",
        "import requests\n"
        "requests.get(u, verify=False)  # seamscan: ignore[SC-CODE-001] reason: pinned CA\n",
    ),
]


def sarif(a: Analysis, known: frozenset[str] = frozenset()) -> dict:
    verdict = decide(a.findings, Policy(), known)
    return json.loads(render_sarif(a.findings, verdict, a.suppressed, ALL_META, "9.9.9"))


def results_by_path(doc: dict) -> dict[str, dict]:
    return {
        r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]: r
        for r in doc["runs"][0]["results"]
    }


def test_output_is_valid_sarif_2_1_0():
    a = analyze(FILES)
    known = frozenset(f.fingerprint for f in a.findings if f.location.path == "svc/b.py")
    jsonschema.Draft4Validator(SCHEMA).validate(sarif(a, known))


def test_driver_lists_every_rule_with_github_severity():
    driver = sarif(analyze(FILES))["runs"][0]["tool"]["driver"]
    assert (driver["name"], driver["version"]) == ("seamscan", "9.9.9")
    assert driver["informationUri"].startswith("https://github.com/")
    rules = {r["id"]: r for r in driver["rules"]}
    assert set(rules) == {m.id for m in ALL_META}
    supa = rules["SC-SUPA-001"]
    assert supa["shortDescription"]["text"] == "Public table without row-level security"
    assert supa["helpUri"].endswith("/src/seamscan/rules/docs/SC-SUPA-001.md")
    assert supa["properties"]["security-severity"] == "8.0"
    assert supa["properties"]["tags"] == ["security", "external/cwe/cwe-284"]
    assert rules["SC-SEC-001"]["properties"]["security-severity"] == "9.5"
    assert rules["SC-CODE-009"]["properties"]["security-severity"] == "5.5"
    assert rules["SC-META-002"]["properties"]["security-severity"] == "3.0"
    assert "tags" not in rules["SC-TEST-001"]["properties"]


def test_each_result_points_at_its_rule_and_location():
    doc = sarif(analyze(FILES))
    rules = doc["runs"][0]["tool"]["driver"]["rules"]
    for r in doc["runs"][0]["results"]:
        assert rules[r["ruleIndex"]]["id"] == r["ruleId"]
        assert len(r["partialFingerprints"]["seamscan/v1"]) == 32
    supa = results_by_path(doc)["supabase/migrations/1_init.sql"]
    assert supa["ruleId"] == "SC-SUPA-001"
    assert supa["locations"][0]["physicalLocation"]["region"]["startLine"] == 1
    [related] = supa["relatedLocations"]
    assert related["physicalLocation"]["artifactLocation"]["uri"] == "src/components/Chat.tsx"
    assert related["physicalLocation"]["region"]["startLine"] == 2


def test_level_follows_severity():
    by_path = results_by_path(sarif(analyze(FILES)))
    assert by_path["svc/a.py"]["level"] == "error"  # HIGH
    assert by_path["svc/my%20file.py"]["level"] == "note"  # LOW (parse failure)


def test_paths_are_percent_encoded_relative_uris():
    assert "svc/my%20file.py" in results_by_path(sarif(analyze(FILES)))


def test_suppressed_and_baselined_results_are_marked():
    a = analyze(FILES)
    known = frozenset(f.fingerprint for f in a.findings if f.location.path == "svc/b.py")
    by_path = results_by_path(sarif(a, known))
    assert by_path["svc/c.py"]["suppressions"] == [
        {"kind": "inSource", "justification": "pinned CA"}
    ]
    assert by_path["svc/b.py"]["baselineState"] == "unchanged"
    assert "baselineState" not in by_path["svc/a.py"]
    assert "suppressions" not in by_path["svc/a.py"]


def test_output_is_byte_identical_regardless_of_input_order():
    def text(files: list[SourceFile]) -> str:
        a = analyze(files)
        return render_sarif(a.findings, decide(a.findings, Policy()), a.suppressed, ALL_META, "1")

    shuffled = FILES[:]
    random.Random(3).shuffle(shuffled)
    assert text(FILES) == text(shuffled)


def many(n: int, severity: Severity) -> list[Finding]:
    return [
        Finding(
            "SC-CODE-002",
            severity,
            Confidence.HIGH,
            Location(f"f{i:05}.py", 1, 1, 1, 2),
            "Swallowed exception",
            "except: pass",
            fingerprint=f"{i:032x}",
        )
        for i in range(n)
    ]


def test_results_are_capped_for_github_and_the_cut_is_stated():
    low = many(MAX_RESULTS, Severity.LOW)
    high = [
        replace(f, location=replace(f.location, path="z.py"), fingerprint="f" * 32)
        for f in many(1, Severity.HIGH)
    ]
    findings = [*low, *high]
    doc = json.loads(render_sarif(findings, decide(findings, Policy()), (), ALL_META, "1"))
    jsonschema.Draft4Validator(SCHEMA).validate(doc)
    run = doc["runs"][0]
    assert len(run["results"]) == MAX_RESULTS == 5000
    assert "z.py" in results_by_path(doc)  # the most severe are kept
    [note] = run["invocations"][0]["toolExecutionNotifications"]
    assert "5,000 of 5,001" in note["message"]["text"]
    assert run["properties"] == {"resultsTotal": 5001, "resultsShown": 5000}


def test_no_cut_notice_under_the_cap():
    run = sarif(analyze(FILES))["runs"][0]
    assert run["invocations"] == [{"executionSuccessful": True}]
    assert "properties" not in run


def test_a_rule_crash_is_a_failed_execution_not_a_result():
    crash = Finding(
        "SC-META-003",
        Severity.LOW,
        Confidence.HIGH,
        Location("<rule SC-CODE-001>", 1, 1, 1, 1),
        "SC-CODE-001 crashed: ValueError: boom",
        "",
        fingerprint="0" * 32,
    )
    doc = json.loads(render_sarif([crash], decide([crash], Policy()), (), ALL_META, "1"))
    jsonschema.Draft4Validator(SCHEMA).validate(doc)
    run = doc["runs"][0]
    assert run["results"] == []
    [invocation] = run["invocations"]
    assert invocation["executionSuccessful"] is False
    [note] = invocation["toolExecutionNotifications"]
    assert note["level"] == "error"
    assert note["message"]["text"] == "SC-CODE-001 crashed: ValueError: boom"


def test_a_finding_without_rule_metadata_fails_loudly():
    a = analyze(FILES)
    with pytest.raises(ValueError, match="SC-CODE-001"):
        render_sarif(a.findings, decide(a.findings, Policy()), (), (), "1")
