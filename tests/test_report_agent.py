"""Spec §10 agent format: one line per finding, capped for a coding agent's context."""

from seamscan.model import Confidence, Finding, Location, Severity
from seamscan.policy.verdict import Policy, decide
from seamscan.report.agent import MAX_CHARS, MAX_LINES, render_agent


def f(
    rule: str,
    severity: Severity,
    confidence: Confidence,
    path: str = "a.py",
    line: int = 1,
    message: str = "m",
    fingerprint: str = "",
) -> Finding:
    return Finding(
        rule,
        severity,
        confidence,
        Location(path, line, 1, line, 2),
        message,
        "evidence",
        fingerprint=fingerprint,
    )


def lines_of(text: str) -> list[str]:
    return text.rstrip("\n").split("\n")


def test_one_line_per_finding_in_the_spec_shape():
    v = decide(
        [f("SC-CODE-001", Severity.HIGH, Confidence.HIGH, "svc/a.py", 7, "bad")],
        Policy(block="all"),
    )
    out = render_agent(v)
    assert lines_of(out) == [
        "seamscan: 1 blocking finding(s)",
        "svc/a.py:7 [SC-CODE-001] bad → seamscan explain SC-CODE-001",
    ]


def test_blocking_first_then_by_severity_then_confidence():
    v = decide(
        [
            f("SC-CODE-002", Severity.MEDIUM, Confidence.HIGH, "a.py", 1),
            f("SC-CODE-006", Severity.HIGH, Confidence.MEDIUM, "b.py", 1),
            f("SC-CODE-001", Severity.HIGH, Confidence.HIGH, "c.py", 1),
            f("SC-SEC-001", Severity.CRITICAL, Confidence.HIGH, "d.py", 1),
            # CRITICAL but doesn't block: still listed after every blocking finding
            f("SC-X-001", Severity.CRITICAL, Confidence.LOW, "e.py", 1),
        ],
        Policy(block="all"),
    )
    rules = [line.split(" ")[1] for line in lines_of(render_agent(v))[1:]]
    assert rules == [
        "[SC-SEC-001]",
        "[SC-CODE-001]",
        "[SC-CODE-006]",
        "[SC-X-001]",
        "[SC-CODE-002]",
    ]


def test_baselined_findings_are_left_out():
    known = f("SC-CODE-001", Severity.HIGH, Confidence.HIGH, fingerprint="k")
    v = decide([known], Policy(block="all"), known=frozenset({"k"}))
    assert lines_of(render_agent(v)) == ["seamscan: No new findings (1 in baseline)"]


def test_blocking_only_drops_the_rest():
    v = decide(
        [
            f("SC-CODE-001", Severity.HIGH, Confidence.HIGH),
            f("SC-CODE-002", Severity.MEDIUM, Confidence.HIGH),
        ],
        Policy(block="all"),
    )
    out = render_agent(v, blocking_only=True)
    assert "SC-CODE-001" in out and "SC-CODE-002" not in out


def test_a_multiline_message_stays_on_one_line():
    v = decide(
        [f("SC-CODE-001", Severity.HIGH, Confidence.HIGH, message="a\n  b")], Policy(block="all")
    )
    assert lines_of(render_agent(v))[1] == "a.py:1 [SC-CODE-001] a b → seamscan explain SC-CODE-001"


def test_capped_at_twenty_lines_and_the_cut_is_stated():
    findings = [f("SC-CODE-001", Severity.HIGH, Confidence.HIGH, "a.py", n) for n in range(1, 35)]
    lines = lines_of(render_agent(decide(findings, Policy(block="all"))))
    assert len(lines) == 1 + MAX_LINES + 1
    assert lines[-1].startswith("… 14 more finding(s) not shown")


def test_total_size_is_capped_even_with_huge_messages():
    findings = [
        f("SC-CODE-001", Severity.HIGH, Confidence.HIGH, "a.py", n, "x" * 5_000)
        for n in range(1, 20)
    ]
    out = render_agent(decide(findings, Policy(block="all")))
    assert len(out) <= MAX_CHARS
    assert "not shown" in lines_of(out)[-1]
    assert all(len(line) < 1_000 for line in lines_of(out))


def test_a_path_too_long_to_fit_still_respects_the_cap():
    findings = [f("SC-CODE-001", Severity.HIGH, Confidence.HIGH, "d/" * 6_000 + "a.py", 1)]
    out = render_agent(decide(findings, Policy(block="all")))
    assert len(out) <= MAX_CHARS
    assert lines_of(out)[-1].startswith("… 1 more finding(s) not shown")


def test_identical_input_gives_identical_output():
    findings = [
        f("SC-CODE-001", Severity.HIGH, Confidence.HIGH, "b.py", 2),
        f("SC-CODE-001", Severity.HIGH, Confidence.HIGH, "a.py", 9),
    ]
    assert render_agent(decide(findings, Policy(block="all"))) == render_agent(
        decide(reversed(findings), Policy(block="all"))
    )
