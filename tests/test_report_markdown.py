"""Spec §10: the markdown audit report a client receives. It must stand on its own."""

import random
import re

from seamscan.analysis import Analysis, analyze
from seamscan.model import Confidence, Finding, Location, Severity, SourceFile
from seamscan.policy.verdict import Policy, decide
from seamscan.report.markdown import render_markdown
from seamscan.rules.registry import ALL_META

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
    SourceFile("svc/broken.py", "def (:\n"),
    SourceFile("svc/err.py", "try:\n    go()\nexcept Exception:\n    pass\n"),
    SourceFile(
        "svc/c.py",
        "import requests\n"
        "requests.get(u, verify=False)  # seamscan: ignore[SC-CODE-001] reason: pinned CA\n",
    ),
]
SKIPPED = (("assets/logo.png", "binary"), ("data/dump.json", "larger than 1 MB"))


def report(
    a: Analysis,
    known: frozenset[str] = frozenset(),
    skipped: tuple[tuple[str, str], ...] = SKIPPED,
) -> str:
    verdict = decide(a.findings, Policy(), known)
    return render_markdown(
        a.findings, verdict, a.suppressed, ALL_META, "9.9.9", a.files_analyzed, skipped
    )


def section(text: str, number: int) -> str:
    match = re.search(rf"^## {number}\. .*?(?=^## |\Z)", text, re.S | re.M)
    assert match, f"section {number} missing"
    return match.group(0)


def test_sections_come_in_the_order_the_spec_gives():
    headings = re.findall(r"^## (.*)$", report(analyze(FILES)), re.M)
    assert headings == [
        "1. Summary",
        "2. Risk at a glance",
        "3. Top findings",
        "4. Other findings",
        "5. Suppressions and baseline",
        "6. Method and limits",
    ]


def test_summary_is_plain_language_with_the_counts():
    summary = section(report(analyze(FILES)), 1)
    assert "seamscan checked 8 files and found 5 issues" in summary
    assert "3 of them should be fixed first" in summary
    assert "SC-" not in summary  # no rule ids for a non-technical reader


def test_summary_for_a_clean_repository_is_calm_and_honest():
    summary = section(report(analyze([SourceFile("ok.py", "x = 1\n")]), skipped=()), 1)
    assert "found no problems" in summary
    assert "not proof" in summary


def test_risk_table_counts_by_category_and_severity():
    table = section(report(analyze(FILES)), 2)
    assert "| Supabase database access | 1 | 0 | 0 | 0 | 1 |" in table
    assert "| Risky code patterns | 0 | 2 | 1 | 0 | 3 |" in table
    assert "| Scan coverage | 0 | 0 | 0 | 1 | 1 |" in table
    assert "| **All areas** | 1 | 2 | 1 | 1 | 5 |" in table
    assert "Firebase" not in table  # areas with nothing found are left out
    assert "1 finding suppressed" in table


def test_top_findings_explain_why_and_how_to_fix_with_evidence():
    top = section(report(analyze(FILES)), 3)
    assert "### 3.1 Public table without row-level security" in top
    assert "anyone holding the project's public anon key" in top  # the rule's summary
    assert "(https://github.com/technoir7/seamscan/blob/main/src/seamscan/rules/docs/SC-SUPA-001.md)" in top
    assert "```sql\ncreate table public.messages" in top
    assert "### 3.2 TLS verification disabled" in top
    assert "Unparseable" not in top and "could not be parsed" not in top  # scan coverage


def test_other_findings_are_grouped_by_area():
    other = section(report(analyze(FILES)), 4)
    assert "### Scan coverage" in other
    assert "`svc/broken.py`" in other


def test_suppressions_and_baseline_list_reasons():
    a = analyze(FILES)
    known = frozenset(f.fingerprint for f in a.findings if f.location.path == "svc/b.py")
    text = report(a, known)
    s5 = section(text, 5)
    assert "SC-CODE-001.md) | `svc/c.py` line 2 | pinned CA |" in s5
    assert "`svc/b.py` line 2" in s5
    assert "`svc/b.py`" not in section(text, 3) + section(text, 4)


def test_method_and_limits_states_version_skips_and_accuracy_caveat():
    method = section(report(analyze(FILES)), 6)
    assert "seamscan 9.9.9" in method
    assert "`assets/logo.png`" in method and "binary" in method
    assert "larger than 1 MB" in method
    assert "written alongside" in method
    assert "https://github.com/technoir7/seamscan#how-well-it-works" in method
    assert "precision" not in method.lower()  # numbers live in the README, not here
    for limit in ("when it runs", "business logic", "outside the repository", "dependencies"):
        assert limit in method.lower()


def test_report_is_deterministic_and_undated():
    shuffled = FILES[:]
    random.Random(5).shuffle(shuffled)
    text = report(analyze(FILES))
    assert text == report(analyze(shuffled))
    assert not re.search(r"\b20\d\d-\d\d-\d\d\b", text)


def hostile(path: str, message: str, evidence: str) -> Finding:
    return Finding(
        "SC-CODE-006",
        Severity.HIGH,
        Confidence.MEDIUM,
        Location(path, 3, 1, 3, 9),
        message,
        evidence,
        fingerprint="a" * 32,
    )


def test_markdown_in_messages_and_evidence_cannot_break_the_layout():
    evil = hostile(
        "x|y.py",
        "Table `a|b` | <script>alert(1)</script> **bold** [x](http://e)",
        "q = f'''\n```\n| col |\n'''",
    )
    other = [replace_rule(evil, "SC-CODE-002", f"{i:032x}") for i in range(6)]
    findings = [evil, *other]
    text = render_markdown(
        findings, decide(findings, Policy()), (), ALL_META, "1", 1, (("we|ird`.bin", "binary"),)
    )
    assert "<script>" not in text
    assert "**bold**" not in text and "[x](http://e)" not in text
    # The evidence fence is longer than any backtick run inside it.
    assert "````python\nq = f'''\n```\n| col |\n'''\n````" in text
    assert "`x|y.py` line 3: Table `a|b` \\| \\<script" in text  # no stray backslashes
    assert "| `x\\|y.py` line 3 | Table `a\\|b` \\| " in text
    assert "``we|ird`.bin``" in text
    tables = re.findall(r"(?:^\|.*\n)+", text, re.M)
    assert len(tables) >= 3
    for table in tables:
        widths = {len(re.split(r"(?<!\\)\|", row)) for row in table.splitlines()}
        assert len(widths) == 1, table  # every row keeps the header's column count


def replace_rule(f: Finding, rule_id: str, fingerprint: str) -> Finding:
    return Finding(
        rule_id, Severity.MEDIUM, f.confidence, f.location, f.message, f.evidence, (), fingerprint
    )


def test_every_rule_has_a_named_area():
    findings = [
        Finding(
            m.id, m.severity, m.confidence, Location("a.py", 1, 1, 1, 2), "m", "e", (), f"{i:032x}"
        )
        for i, m in enumerate(ALL_META)
    ]
    text = render_markdown(findings, decide(findings, Policy()), (), ALL_META, "1", 1, ())
    assert "SC-" in text  # rendered without a missing-category error


def test_top_findings_cover_every_kind_of_issue_to_fix_first():
    blocking = [m for m in ALL_META if m.severity >= Severity.HIGH and m.confidence >= 2]
    findings = [
        Finding(
            m.id,
            m.severity,
            m.confidence,
            Location(f"f{i}.py", 1, 1, 1, 2),
            "m",
            "e",
            (),
            f"{i:032x}",
        )
        for i, m in enumerate(blocking)
    ]
    top = section(
        render_markdown(findings, decide(findings, Policy()), (), ALL_META, "1", 1, ()), 3
    )
    assert len(blocking) > 10
    for m in blocking:
        assert m.title in top
    assert "Swallowed exception" not in section(report(analyze(FILES)), 3)  # not blocking


def test_without_anything_to_fix_first_the_most_severe_are_explained():
    a = analyze([SourceFile("svc/err.py", "try:\n    go()\nexcept Exception:\n    pass\n")])
    assert "### 3.1 Swallowed exception" in section(report(a), 3)
