from seamscan.analysis import analyze
from seamscan.model import SourceFile
from seamscan.policy.verdict import Policy, decide
from seamscan.report.terminal import render_terminal

VERIFY_OFF = "import requests\nrequests.get(u, verify=False)\n"
SUPPRESSED = SourceFile(
    "s.py",
    "import requests\n"
    "requests.get(u, verify=False)  # seamscan: ignore[SC-CODE-001] reason: test server\n",
)


def test_no_extra_line_when_nothing_is_suppressed_or_baselined():
    a = analyze([SourceFile("a.py", VERIFY_OFF)])
    out = render_terminal(a.findings, decide(a.findings, Policy()), a.suppressed)
    assert "suppressed" not in out and "baseline" not in out


def test_one_short_line_counts_suppressed_and_baselined():
    a = analyze([SourceFile("a.py", VERIFY_OFF), SourceFile("b.py", VERIFY_OFF), SUPPRESSED])
    known = frozenset(f.fingerprint for f in a.findings if f.location.path == "a.py")
    out = render_terminal(a.findings, decide(a.findings, Policy(), known), a.suppressed)
    assert out.splitlines()[-2] == "seamscan: 1 suppressed inline, 1 in baseline (see --stats)"
    assert out.splitlines()[-1] == "seamscan: 1 blocking finding(s)"
