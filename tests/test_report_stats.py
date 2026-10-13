"""--stats (spec §9.2, §11.1): what was analyzed, skipped and set aside, and why."""

from seamscan.analysis import analyze
from seamscan.model import SourceFile
from seamscan.policy.verdict import Policy, decide
from seamscan.report.stats import render_stats

VERIFY_OFF = "import requests\nrequests.get(u, verify=False)\n"
FILES = [
    SourceFile("a.py", VERIFY_OFF),
    SourceFile("b.py", VERIFY_OFF),
    SourceFile("broken.py", "def (:\n"),
    SourceFile(
        "c.py",
        "import requests\n"
        "requests.get(u, verify=False)  # seamscan: ignore[SC-CODE-001] reason: test server\n",
    ),
]


def test_stats_count_files_findings_and_set_aside():
    a = analyze(FILES)
    known = frozenset(f.fingerprint for f in a.findings if f.location.path == "a.py")
    verdict = decide(a.findings, Policy(block="all"), known)
    skipped = (("logo.png", "binary"), ("dump.json", "larger than 1 MB"))
    assert render_stats(a.findings, verdict, a.suppressed, a.files_analyzed, skipped) == (
        "seamscan stats\n"
        "  files analyzed: 4\n"
        "  files skipped: 2\n"
        "    dump.json: larger than 1 MB\n"
        "    logo.png: binary\n"
        "  findings: 3 (HIGH 2, LOW 1)\n"
        "  blocking: 1\n"
        "  baselined: 1\n"
        "  suppressed: 1\n"
        "    c.py:2 SC-CODE-001: test server\n"
    )


def test_stats_with_nothing_found():
    a = analyze([SourceFile("ok.py", "x = 1\n")])
    out = render_stats(a.findings, decide(a.findings, Policy(block="all")), a.suppressed, 1, ())
    assert "  findings: 0\n" in out and "  suppressed: 0\n" in out


def test_stats_say_where_dependency_facts_came_from():
    from seamscan.report.stats import DependencyCounts

    a = analyze([SourceFile("ok.py", "x = 1\n")])
    counts = DependencyCounts(network=3, cache=2, snapshot=30, unverified=1, not_looked_up=4)
    out = render_stats(
        a.findings, decide(a.findings, Policy(block="all")), a.suppressed, 1, (), counts
    )
    assert out.endswith(
        "  dependencies checked: 36 (network 3, cache 2, snapshot 30)\n"
        "    not verified: 1\n"
        "    not looked up (allowed or private): 4\n"
    )


def test_stats_without_dependencies_say_so():
    from seamscan.report.stats import DependencyCounts

    a = analyze([SourceFile("ok.py", "x = 1\n")])
    out = render_stats(
        a.findings, decide(a.findings, Policy(block="all")), a.suppressed, 1, (), DependencyCounts()
    )
    assert out.endswith("  dependencies checked: 0\n")
