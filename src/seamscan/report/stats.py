"""`--stats`: what a run analyzed, skipped and set aside (spec §9.2, §11.1).

Printed to stderr, so stdout stays machine-readable whatever the format.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from seamscan.model import Finding, Severity
from seamscan.policy.suppress import Suppressed
from seamscan.policy.verdict import Verdict


def render_stats(
    findings: Sequence[Finding],
    verdict: Verdict,
    suppressed: Sequence[Suppressed],
    files_analyzed: int,
    skipped: Sequence[tuple[str, str]],
) -> str:
    by_sev = Counter(f.severity for f in findings)
    breakdown = ", ".join(
        f"{s.name} {by_sev[s]}" for s in sorted(Severity, reverse=True) if by_sev[s]
    )
    lines = [
        "seamscan stats",
        f"  files analyzed: {files_analyzed}",
        f"  files skipped: {len(skipped)}",
        *(f"    {path}: {reason}" for path, reason in sorted(skipped)),
        f"  findings: {len(findings)}" + (f" ({breakdown})" if breakdown else ""),
        f"  blocking: {len(verdict.blocking)}",
        f"  baselined: {len(verdict.baselined)}",
        f"  suppressed: {len(suppressed)}",
        *(
            f"    {s.finding.location.path}:{s.finding.location.start_line} "
            f"{s.finding.rule_id}: {s.reason}"
            for s in sorted(suppressed, key=lambda s: s.finding.sort_key())
        ),
    ]
    return "\n".join(lines) + "\n"
