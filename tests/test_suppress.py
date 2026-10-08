from bench.fake_secrets import FAKES
from seamscan.analysis import analyze
from seamscan.model import ChangeSet, SourceFile

VERIFY_OFF = "requests.get(u, verify=False)"


def run(src: str):
    return analyze([SourceFile("a.py", "import requests\n" + src)])


def rules(findings) -> list[str]:
    return [f.rule_id for f in findings]


def suppressed_rules(a) -> list[str]:
    return [s.finding.rule_id for s in a.suppressed]


def test_same_line_suppression_with_reason():
    a = run(
        f"{VERIFY_OFF}  # seamscan: ignore[SC-CODE-001] reason: internal CA pinned in INFRA-12\n"
    )
    assert rules(a.findings) == []
    assert suppressed_rules(a) == ["SC-CODE-001"]


def test_next_line_suppression():
    a = run(
        f"# seamscan: ignore-next-line[SC-CODE-001] reason: test fixture server\n{VERIFY_OFF}\n"
    )
    assert rules(a.findings) == [] and suppressed_rules(a) == ["SC-CODE-001"]


def test_suppression_without_reason_does_not_apply_and_is_reported():
    a = run(f"{VERIFY_OFF}  # seamscan: ignore[SC-CODE-001]\n")
    assert sorted(rules(a.findings)) == ["SC-CODE-001", "SC-META-001"]
    assert not a.suppressed


def test_suppression_for_a_different_rule_does_not_apply():
    a = run(f"{VERIFY_OFF}  # seamscan: ignore[SC-CODE-002] reason: unrelated\n")
    assert rules(a.findings) == ["SC-CODE-001"]


def test_suppressed_findings_carry_their_reason_and_fingerprint():
    a = run(
        f"{VERIFY_OFF}  # seamscan: ignore[SC-CODE-001] reason: internal CA pinned in INFRA-12\n"
    )
    [s] = a.suppressed
    assert s.reason == "internal CA pinned in INFRA-12"
    assert len(s.finding.fingerprint) == 32


def test_scan_mode_keeps_the_reason():
    src = f"import requests\n{VERIFY_OFF}  # seamscan: ignore[SC-CODE-001] reason: test server\n"
    a = analyze([SourceFile("a.py", src)], change=ChangeSet(added={"a.py": ((2, 2),)}))
    assert [s.reason for s in a.suppressed] == ["test server"]


def test_a_secret_written_into_a_reason_is_redacted():
    key = FAKES["FAKE_STRIPE_LIVE"]
    a = run(f"{VERIFY_OFF}  # seamscan: ignore[SC-CODE-001] reason: rotated {key} already\n")
    [s] = a.suppressed
    assert key not in s.reason
    assert s.reason.startswith("rotated sk_live_") and s.reason.endswith(" already")


def test_analysis_counts_the_files_it_analyzed():
    a = analyze([SourceFile("a.py", "x = 1\n"), SourceFile("b.sql", "select 1;\n")])
    assert a.files_analyzed == 2
