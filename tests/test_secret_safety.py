"""Spec §6.4: no output format ever contains a full secret value."""

from bench.case import case_files, load_all
from bench.fake_secrets import FAKES
from seamscan.analysis import analyze
from seamscan.policy.verdict import Policy, decide
from seamscan.report.json import render_json
from seamscan.report.terminal import render_terminal


def test_no_reporter_prints_a_full_fake_secret():
    for case in load_all():
        result = analyze(case_files(case))
        findings = (*result.findings, *result.suppressed)
        verdict = decide(findings, Policy())
        outputs = render_json(findings, verdict, "test") + render_terminal(findings, verdict)
        for name, value in FAKES.items():
            assert value not in outputs, f"{case.id}: {name} printed in full"
