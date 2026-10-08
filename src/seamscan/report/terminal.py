"""Human-readable output. The summary line comes from the same Verdict as the exit code."""

from __future__ import annotations

from collections.abc import Sequence
from itertools import groupby

from seamscan.model import Finding
from seamscan.policy.suppress import Suppressed
from seamscan.policy.verdict import Verdict


def render_terminal(
    findings: Sequence[Finding], verdict: Verdict, suppressed: Sequence[Suppressed] = ()
) -> str:
    blocking = {f.fingerprint for f in verdict.blocking}
    lines: list[str] = []
    ordered = sorted(findings, key=Finding.sort_key)
    for path, group in groupby(ordered, key=lambda f: f.location.path):
        lines.append(path)
        for f in group:
            mark = "BLOCK" if f.fingerprint in blocking else "note "
            lines.append(
                f"  {f.location.start_line:>5}  {mark}  {f.rule_id}  "
                f"{f.severity.name}/{f.confidence.name}  {f.message}"
            )
        lines.append("")
    hidden = [
        text
        for count, text in (
            (len(suppressed), f"{len(suppressed)} suppressed inline"),
            (len(verdict.baselined), f"{len(verdict.baselined)} in baseline"),
        )
        if count
    ]
    if hidden:
        lines.append(f"seamscan: {', '.join(hidden)} (see --stats)")
    lines.append(f"seamscan: {verdict.headline}")
    return "\n".join(lines) + "\n"
