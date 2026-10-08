"""Spec §6.4: no output format ever contains a full secret value."""

from bench.case import case_files, load_all
from bench.fake_secrets import FAKES
from seamscan.analysis import analyze
from seamscan.model import SourceFile
from seamscan.policy.verdict import Policy, decide
from seamscan.report.agent import render_agent
from seamscan.report.json import render_json
from seamscan.report.markdown import render_markdown
from seamscan.report.sarif import render_sarif
from seamscan.report.stats import render_stats
from seamscan.report.terminal import render_terminal
from seamscan.rules.registry import ALL_META


def every_output(files: tuple[SourceFile, ...]) -> str:
    a = analyze(files)
    # Baseline half of the findings, so the baselined paths of each format run too.
    known = frozenset(f.fingerprint for f in a.findings[::2])
    verdict = decide(a.findings, Policy(), known)
    return "".join(
        (
            render_json(a.findings, verdict, "test", a.suppressed),
            render_terminal(a.findings, verdict, a.suppressed),
            render_sarif(a.findings, verdict, a.suppressed, ALL_META, "test"),
            render_markdown(
                a.findings, verdict, a.suppressed, ALL_META, "test", a.files_analyzed, ()
            ),
            render_stats(a.findings, verdict, a.suppressed, a.files_analyzed, ()),
            render_agent(verdict),
            # The agent format has no suppressed section; render those findings too.
            render_agent(decide([s.finding for s in a.suppressed], Policy())),
        )
    )


def test_no_reporter_prints_a_full_fake_secret():
    for case in load_all():
        outputs = every_output(case_files(case))
        for name, value in FAKES.items():
            assert value not in outputs, f"{case.id}: {name} printed in full"


def test_a_secret_in_a_suppression_reason_is_never_printed_in_full():
    key = FAKES["FAKE_STRIPE_LIVE"]
    src = (
        "import requests\n"
        f"requests.get(u, verify=False)  # seamscan: ignore[SC-CODE-001] reason: was {key}\n"
    )
    outputs = every_output((SourceFile("a.py", src),))
    assert "SC-CODE-001" in outputs
    assert key not in outputs
