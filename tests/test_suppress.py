from seamscan.analysis import analyze
from seamscan.model import SourceFile

VERIFY_OFF = "requests.get(u, verify=False)"


def run(src: str):
    return analyze([SourceFile("a.py", "import requests\n" + src)])


def rules(findings) -> list[str]:
    return [f.rule_id for f in findings]


def test_same_line_suppression_with_reason():
    a = run(
        f"{VERIFY_OFF}  # seamscan: ignore[SC-CODE-001] reason: internal CA pinned in INFRA-12\n"
    )
    assert rules(a.findings) == []
    assert rules(a.suppressed) == ["SC-CODE-001"]


def test_next_line_suppression():
    a = run(
        f"# seamscan: ignore-next-line[SC-CODE-001] reason: test fixture server\n{VERIFY_OFF}\n"
    )
    assert rules(a.findings) == [] and rules(a.suppressed) == ["SC-CODE-001"]


def test_suppression_without_reason_does_not_apply_and_is_reported():
    a = run(f"{VERIFY_OFF}  # seamscan: ignore[SC-CODE-001]\n")
    assert sorted(rules(a.findings)) == ["SC-CODE-001", "SC-META-001"]
    assert not a.suppressed


def test_suppression_for_a_different_rule_does_not_apply():
    a = run(f"{VERIFY_OFF}  # seamscan: ignore[SC-CODE-002] reason: unrelated\n")
    assert rules(a.findings) == ["SC-CODE-001"]
