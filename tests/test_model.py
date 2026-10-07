from seamscan.model import Confidence, Finding, Location, Severity, with_fingerprints


def finding(path: str = "app.py", line: int = 3, evidence: str = "requests.get(u, verify=False)"):
    return Finding(
        rule_id="SC-CODE-001",
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        location=Location(path, line, 5, line, 40),
        message="TLS verification disabled",
        evidence=evidence,
    )


def test_fingerprint_survives_line_shift_and_whitespace():
    (a,) = with_fingerprints([finding(line=3)])
    (b,) = with_fingerprints([finding(line=40, evidence="requests.get(u,   verify=False)")])
    assert a.fingerprint and a.fingerprint == b.fingerprint


def test_fingerprint_changes_when_code_changes():
    (a,) = with_fingerprints([finding(evidence="requests.get(u, verify=False)")])
    (b,) = with_fingerprints([finding(evidence="httpx.get(u, verify=False)")])
    assert a.fingerprint != b.fingerprint


def test_identical_snippets_in_one_file_get_distinct_fingerprints():
    a, b = with_fingerprints([finding(line=3), finding(line=9)])
    assert a.fingerprint != b.fingerprint
