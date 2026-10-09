from seamscan.model import Confidence, Finding, Location, Severity
from seamscan.policy.verdict import Policy, decide


def f(rule: str, severity: Severity, confidence: Confidence) -> Finding:
    return Finding(rule, severity, confidence, Location("a.py", 1, 1, 1, 2), "m", "e")


def test_high_severity_medium_confidence_blocks():
    v = decide([f("SC-CODE-006", Severity.HIGH, Confidence.MEDIUM)], Policy())
    assert v.exit_code == 1 and len(v.blocking) == 1


def test_low_confidence_does_not_block():
    v = decide([f("SC-DEP-002", Severity.HIGH, Confidence.LOW)], Policy())
    assert v.exit_code == 0 and not v.blocking and len(v.non_blocking) == 1


def test_medium_severity_does_not_block_by_default():
    v = decide([f("SC-CODE-002", Severity.MEDIUM, Confidence.HIGH)], Policy())
    assert v.exit_code == 0


def test_rule_crash_is_an_internal_error():
    v = decide([f("SC-META-003", Severity.LOW, Confidence.HIGH)], Policy())
    assert v.exit_code == 3


def test_clean_run():
    v = decide([], Policy())
    assert v.exit_code == 0 and v.headline == "No findings"


def test_known_findings_are_reported_but_never_block():
    known = Finding(
        "SC-CODE-001",
        Severity.HIGH,
        Confidence.HIGH,
        Location("a.py", 1, 1, 1, 2),
        "m",
        "e",
        fingerprint="abc",
    )
    v = decide([known], Policy(), known=frozenset({"abc"}))
    assert v.exit_code == 0 and not v.blocking and v.baselined == (known,)
    assert v.headline == "No new findings (1 in baseline)"


def test_a_swallowed_write_is_reported_but_does_not_block():
    # ADR-005: SC-CODE-002 measured 4 real of 14 on 40 public repositories, so its
    # confidence is LOW: it shows up in every report and never fails a build alone.
    from seamscan.analysis import analyze
    from seamscan.model import SourceFile

    src = (
        "import stripe\n\ndef refund(cid):\n    try:\n        stripe.Refund.create(charge=cid)\n"
        "    except Exception:\n        pass\n    mark_refunded(cid)\n"
    )
    found = analyze([SourceFile("app/billing.py", src)]).findings
    assert [f.rule_id for f in found] == ["SC-CODE-002"]
    assert decide(found, Policy()).blocking == ()
