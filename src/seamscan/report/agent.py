"""Agent output (spec §10): compact lines a coding agent can act on, sized for hook context.

`path:line [RULE] message → seamscan explain RULE`. The fix is a pointer to the rule page,
not text pulled from it: messages already name the culprit and usually the remedy, the
"How to fix" sections are multi-paragraph with code, and the page is offline and complete.

Blocking findings come first, then rule crashes, then the rest, each by severity and
confidence. Baselined findings are known debt and left out. At most MAX_LINES findings
and MAX_CHARS characters in total; a final line says how many were cut.
"""

from __future__ import annotations

import re

from seamscan.model import Finding
from seamscan.policy.verdict import Verdict

MAX_LINES = 20
# Claude Code moves hook text over 10,000 characters to a file the agent isn't asked
# to read; this stays well inside that.
MAX_CHARS = 8_000
MAX_MESSAGE = 400

_WHITESPACE = re.compile(r"\s+")


def _line(f: Finding) -> str:
    message = _WHITESPACE.sub(" ", f.message).strip()
    if len(message) > MAX_MESSAGE:
        message = message[: MAX_MESSAGE - 1] + "…"
    return (
        f"{f.location.path}:{f.location.start_line} [{f.rule_id}] {message}"
        f" → seamscan explain {f.rule_id}"
    )


def _ordered(verdict: Verdict, blocking_only: bool) -> list[Finding]:
    tiers = [verdict.blocking]
    if not blocking_only:
        tiers += [verdict.internal_errors, verdict.non_blocking]
    ordered: list[Finding] = []
    for tier in tiers:
        ordered.extend(sorted(tier, key=lambda f: (-f.severity, -f.confidence, *f.sort_key())))
    return ordered


def _cut(hidden: int) -> str:
    return (
        f"… {hidden} more finding(s) not shown (agent output keeps {MAX_LINES} lines,"
        f" {MAX_CHARS:,} chars); `--format terminal` lists all"
    )


def render_agent(verdict: Verdict, blocking_only: bool = False) -> str:
    findings = _ordered(verdict, blocking_only)
    lines = [f"seamscan: {verdict.headline}"]
    # Reserve room for the cut line up front so adding it can never break the cap.
    budget = MAX_CHARS - len(lines[0]) - 1 - len(_cut(len(findings))) - 1
    shown = 0
    for f in findings[:MAX_LINES]:
        line = _line(f)
        if len(line) + 1 > budget:
            break
        lines.append(line)
        budget -= len(line) + 1
        shown += 1
    if shown < len(findings):
        lines.append(_cut(len(findings) - shown))
    return "\n".join(lines) + "\n"
