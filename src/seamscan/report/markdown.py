"""The markdown audit report: the deliverable a client reads (spec §10).

Written for a non-technical reader first. Deterministic and undated: whoever hands it
over adds the date and the client's name.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from itertools import groupby

from seamscan.model import Finding, RuleMeta, Severity
from seamscan.policy.suppress import Suppressed
from seamscan.policy.verdict import Verdict

ACCURACY_URI = "https://github.com/technoir7/seamscan#how-well-it-works"
# With nothing to fix first, this many kinds of issue are still explained in full.
TOP_GROUPS = 3
EXAMPLES_PER_GROUP = 3  # places shown with evidence per kind of issue
SKIPPED_PER_REASON = 20

# Keyed by the middle part of a rule id (SC-<AREA>-NNN), in the order the report uses:
# (heading, the same words mid-sentence).
AREAS = {
    "SEC": ("Secrets and keys", "secrets and keys"),
    "SUPA": ("Supabase database access", "Supabase database access"),
    "FIRE": ("Firebase security rules", "Firebase security rules"),
    "WEB": ("Web routes and server settings", "web routes and server settings"),
    "CODE": ("Risky code patterns", "risky code patterns"),
    "TEST": ("Tests that can't catch bugs", "tests that can't catch bugs"),
    "META": ("Scan coverage", "scan coverage"),
}
_SEVERITIES = (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW)
_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".sql": "sql",
    ".json": "json",
}
_SPECIAL = re.compile(r"([\\`*_\[\]<>|~&#!])")
_SPAN = re.compile(r"`([^`]+)`")
_BACKTICKS = re.compile(r"`+")
_SPACE = re.compile(r"\s+")


def _area(rule_id: str) -> str:
    return rule_id.split("-")[1]


def _area_order(rule_id: str) -> int:
    return list(AREAS).index(_area(rule_id))


def _plural(n: int, word: str, words: str | None = None) -> str:
    return f"{n:,} {word if n == 1 else (words or word + 's')}"


def _sev(s: Severity) -> str:
    return s.name.capitalize()


# --- Escaping: text from scanned code must never change the report's structure. ---


def _text(s: str) -> str:
    return _SPECIAL.sub(r"\\\1", _SPACE.sub(" ", s))


def _code(s: str, table: bool = False) -> str:
    """An inline code span that holds any text."""
    s = _SPACE.sub(" ", s)
    if table:
        # GFM splits table cells on `|` even inside code spans, unless escaped; outside
        # tables the backslash would show, since code spans take no escapes.
        s = s.replace("|", "\\|")
    fence = "`" * (max((len(m) for m in _BACKTICKS.findall(s)), default=0) + 1)
    pad = " " if s.startswith(("`", " ")) or s.endswith(("`", " ")) else ""
    return f"{fence}{pad}{s}{pad}{fence}"


def _inline(s: str, table: bool = False) -> str:
    """Rule messages mark code with backticks; keep those spans, escape everything else."""
    s = " ".join(s.split())
    out: list[str] = []
    pos = 0
    for m in _SPAN.finditer(s):
        out += [_text(s[pos : m.start()]), _code(m.group(1), table)]
        pos = m.end()
    out.append(_text(s[pos:]))
    return "".join(out)


def _fence(code: str, path: str) -> str:
    longest = max((len(m) for m in _BACKTICKS.findall(code)), default=0)
    fence = "`" * max(3, longest + 1)
    lang = next((v for k, v in _LANGUAGES.items() if path.endswith(k)), "")
    return f"{fence}{lang}\n{code.strip(chr(10))}\n{fence}"


def _where(f: Finding, table: bool = False) -> str:
    return f"{_code(f.location.path, table)} line {f.location.start_line}"


def _table(header: Sequence[str], rows: Iterable[Sequence[str]]) -> list[str]:
    return [
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---" for _ in header) + "|",
        *("| " + " | ".join(row) + " |" for row in rows),
    ]


def _issue(meta: RuleMeta) -> str:
    return f"[{_text(meta.title)}]({meta.help_uri})"


def _rank(f: Finding) -> tuple[int, int, int, tuple[object, ...]]:
    return (-f.severity, -f.confidence, _area_order(f.rule_id), f.sort_key())


# --- Sections ---


def _summary(
    active: Sequence[Finding],
    verdict: Verdict,
    files_analyzed: int,
    hidden: int,
) -> list[str]:
    lines: list[str] = []
    if verdict.internal_errors:
        lines += [
            f"**This report is incomplete.** {_plural(len(verdict.internal_errors), 'check')} "
            "failed to run, so problems they look for may be missing. Section 4 names them.",
            "",
        ]
    checked = f"seamscan checked {_plural(files_analyzed, 'file')}"
    sentences: list[str] = []
    if not active:
        sentences.append(f"{checked} and found no problems that need attention.")
    else:
        by_sev = Counter(f.severity for f in active)
        breakdown = ", ".join(f"{by_sev[s]} {s.name.lower()}" for s in _SEVERITIES if by_sev[s])
        sentences.append(f"{checked} and found {_plural(len(active), 'issue')} ({breakdown}).")
        if verdict.blocking:
            sentences.append(
                f"{len(verdict.blocking):,} of them should be fixed first: each would do "
                "serious harm if real, and is likely to be real."
            )
        else:
            sentences.append(
                "None of them is both high-impact and likely to be real, so none needs to hold "
                "up a release. They are still worth fixing."
            )
        areas = Counter(_area(f.rule_id) for f in active if _area(f.rule_id) != "META")
        top = sorted(areas.items(), key=lambda kv: (-kv[1], list(AREAS).index(kv[0])))[:2]
        if top:
            named = " and ".join(f"{AREAS[a][1]} ({n})" for a, n in top)
            sentences.append(f"Most of them concern {named}.")
    if hidden == 1:
        sentences.append(
            "Separately, 1 finding was set aside by the team; section 5 lists it with the reason."
        )
    elif hidden:
        sentences.append(
            f"Separately, {hidden:,} findings were set aside by the team; section 5 lists "
            "them with the reasons."
        )
    lines += [" ".join(sentences), ""]
    if active:
        lines.append(
            "Each finding is a lead for an engineer to confirm, not proof that anything has "
            "been broken into. Sections 3 and 4 explain each one and how to fix it."
        )
    else:
        lines.append(
            "That is a good sign, but not proof that the code is secure: section 6 explains "
            "what an automated check can and can't see."
        )
    return lines


def _risk_table(active: Sequence[Finding], suppressed: int, baselined: int) -> list[str]:
    if not active:
        lines = ["No open findings."]
    else:
        counts = Counter((_area(f.rule_id), f.severity) for f in active)
        present = [a for a in AREAS if any(counts[(a, s)] for s in _SEVERITIES)]
        rows = [
            [
                AREAS[a][0],
                *(str(counts[(a, s)]) for s in _SEVERITIES),
                str(sum(counts[(a, s)] for s in _SEVERITIES)),
            ]
            for a in present
        ]
        totals = [str(sum(1 for f in active if f.severity == s)) for s in _SEVERITIES]
        rows.append(["**All areas**", *totals, str(len(active))])
        lines = _table(["Area", *(_sev(s) for s in _SEVERITIES), "Total"], rows)
        lines += [
            "",
            "Severity is how much harm a problem could do if it is real, from critical down "
            "to low. How likely each one is to be real is a separate judgment, made by the "
            "check that found it.",
        ]
    notes = [
        text
        for n, text in (
            (suppressed, f"{_plural(suppressed, 'finding')} suppressed in the code"),
            (baselined, f"{_plural(baselined, 'finding')} accepted into the baseline"),
        )
        if n
    ]
    if notes:
        lines += ["", f"Not counted here: {' and '.join(notes)} (section 5)."]
    return lines


def _top(
    active: Sequence[Finding], verdict: Verdict, meta: dict[str, RuleMeta]
) -> tuple[list[str], set[str]]:
    """The kinds of issue to fix first, explained in full. Returns the fingerprints shown.

    Every kind with a finding to fix first is covered, so the summary's count and this
    section agree; there are at most as many kinds as rules, which keeps it bounded.
    """
    groups: dict[str, list[Finding]] = {}
    for f in sorted(active, key=_rank):
        if _area(f.rule_id) != "META" and f.severity >= Severity.MEDIUM:
            groups.setdefault(f.rule_id, []).append(f)
    ranked = sorted(groups.values(), key=lambda g: (*_rank(g[0])[:2], -len(g), g[0].rule_id))
    fix_first = {f.rule_id for f in verdict.blocking}
    if fix_first:
        chosen = [g for g in ranked if g[0].rule_id in fix_first]
        intro = "The issues to fix first, one heading per kind of issue."
    else:
        chosen = ranked[:TOP_GROUPS]
        intro = "Nothing here needs to hold up a release; these are the most serious issues."
    if not chosen:
        return [
            "No high- or medium-severity findings. Anything else is listed in section 4."
        ], set()
    lines = [
        f"{intro} Each shows the code that triggered it (secrets are shortened, never shown "
        "in full), why it matters and how to fix it.",
    ]
    shown: set[str] = set()
    for n, group in enumerate(chosen, start=1):
        m = meta[group[0].rule_id]
        lines += [
            "",
            f"### 3.{n} {_text(m.title)}",
            "",
            f"**{_sev(group[0].severity)}** · {AREAS[_area(m.id)][0]} · `{m.id}` · "
            f"found in {_plural(len(group), 'place')}",
            "",
            f"**Why it matters.** {_inline(m.summary)}",
            "",
            f"**How to fix it.** The [{m.id} rule page]({m.help_uri}) explains the fix and "
            "shows a safe pattern.",
        ]
        for f in group[:EXAMPLES_PER_GROUP]:
            shown.add(f.fingerprint)
            lines += ["", f"{_where(f)}: {_inline(f.message)}"]
            if f.evidence.strip():
                lines += ["", _fence(f.evidence, f.location.path)]
        rest = len(group) - EXAMPLES_PER_GROUP
        if rest > 0:
            lines += [
                "",
                f"{_plural(rest, 'more place')} {'is' if rest == 1 else 'are'} "
                "listed in section 4.",
            ]
    return lines, shown


def _finding_rows(findings: Iterable[Finding], meta: dict[str, RuleMeta]) -> list[list[str]]:
    return [
        [_sev(f.severity), _issue(meta[f.rule_id]), _where(f, True), _inline(f.message, True)]
        for f in findings
    ]


def _others(remaining: Sequence[Finding], meta: dict[str, RuleMeta]) -> list[str]:
    if not remaining:
        return ["Nothing else to report."]
    lines = ["Every other finding, grouped by area. Each issue links to a page that explains it."]
    ordered = sorted(remaining, key=lambda f: (_area_order(f.rule_id), *_rank(f)))
    for area, group in groupby(ordered, key=lambda f: _area(f.rule_id)):
        lines += ["", f"### {AREAS[area][0]}", ""]
        lines += _table(["Severity", "Issue", "Where", "Detail"], _finding_rows(group, meta))
    return lines


def _set_aside(
    suppressed: Sequence[Suppressed], baselined: Sequence[Finding], meta: dict[str, RuleMeta]
) -> list[str]:
    if not suppressed and not baselined:
        return ["No findings were suppressed or accepted into a baseline."]
    lines: list[str] = []
    if suppressed:
        rows = [
            [_issue(meta[s.finding.rule_id]), _where(s.finding, True), _inline(s.reason, True)]
            for s in sorted(suppressed, key=lambda s: s.finding.sort_key())
        ]
        lines += [
            "### Suppressed in the code",
            "",
            "The team marked these as safe with a comment in the code that gives a reason. "
            "They don't count against the result, so check that each reason still holds.",
            "",
            *_table(["Issue", "Where", "Reason given"], rows),
        ]
    if baselined:
        if lines:
            lines.append("")
        lines += [
            "### Accepted into the baseline",
            "",
            "These were recorded as known issues to fix later. They are still in the code; "
            "they are listed here so they aren't forgotten.",
            "",
            *_table(
                ["Severity", "Issue", "Where", "Detail"],
                _finding_rows(sorted(baselined, key=_rank), meta),
            ),
        ]
    return lines


def _method(
    rules: Sequence[RuleMeta],
    tool_version: str,
    files_analyzed: int,
    skipped: Sequence[tuple[str, str]],
) -> list[str]:
    checks = sorted((m for m in rules if _area(m.id) != "META"), key=lambda m: m.id)
    lines = [
        "### What seamscan checks",
        "",
        "seamscan reads the code and configuration in the repository without running "
        "anything, and looks for the security and reliability problems that AI coding tools "
        f"often introduce. This run used {_plural(len(checks), 'check')}:",
        "",
    ]
    by_area = groupby(sorted(checks, key=lambda m: _area_order(m.id)), key=lambda m: _area(m.id))
    for area, group in by_area:
        titles = "; ".join(_text(m.title) for m in sorted(group, key=lambda m: m.id))
        lines.append(f"- **{AREAS[area][0]}:** {titles}.")
    lines += [
        "",
        "### What it can't see",
        "",
        "- **How the application behaves when it runs.** Nothing is executed, so problems "
        "that only show up at run time, or depend on data, can be missed.",
        "- **Business logic.** It can't tell whether the right person is allowed to do the "
        "right thing in your product, only whether common safeguards are present.",
        "- **Anything outside the repository**: settings made in the Supabase or Firebase "
        "dashboards, cloud permissions, and environment variables set on servers.",
        "- **Third-party dependencies.** Known-vulnerable or malicious packages are not "
        "checked yet.",
        "- **Other kinds of file.** It reads Python, TypeScript and JavaScript, Supabase SQL "
        "migrations, Firebase rules and environment files.",
        "",
        "Like any automated check it can raise a false alarm or miss a real problem, so a "
        "clean result is not proof that the code is secure.",
        "",
        "### How accurate it is",
        "",
        "Each check is tested against a set of labelled examples, including near-misses it "
        "must not flag. Those examples were written alongside the checks, so they show the "
        "checks do what they were designed to do; they don't yet measure how often a check is "
        f"wrong on code like yours. Current figures: [How well it works]({ACCURACY_URI}).",
        "",
        "### This run",
        "",
        f"- Tool: seamscan {_text(tool_version)}",
        f"- Files analyzed: {files_analyzed:,}",
        f"- Files skipped: {len(skipped):,}",
    ]
    for reason, group in groupby(sorted(skipped, key=lambda s: (s[1], s[0])), key=lambda s: s[1]):
        paths = [p for p, _ in group]
        shown = ", ".join(_code(p) for p in paths[:SKIPPED_PER_REASON])
        more = len(paths) - SKIPPED_PER_REASON
        lines.append(
            f"  - {_text(reason)} ({len(paths):,}): {shown}"
            + (f", and {more:,} more" if more > 0 else "")
        )
    lines += [
        "",
        "Folders of installed packages and build output (such as `node_modules` and `dist`) "
        "and files ignored by git are not read.",
    ]
    return lines


def render_markdown(
    findings: Sequence[Finding],
    verdict: Verdict,
    suppressed: Sequence[Suppressed],
    rules: Sequence[RuleMeta],
    tool_version: str,
    files_analyzed: int,
    skipped: Sequence[tuple[str, str]],
) -> str:
    """`rules` must describe every rule id that can appear; the report layer can't look them up."""
    meta = {m.id: m for m in rules}
    used = {f.rule_id for f in findings} | {s.finding.rule_id for s in suppressed}
    missing = sorted(used - meta.keys())
    if missing:
        raise ValueError(f"no rule metadata for {', '.join(missing)}")
    baselined_fps = {f.fingerprint for f in verdict.baselined}
    active = [f for f in findings if f.fingerprint not in baselined_fps]
    hidden = len(suppressed) + len(verdict.baselined)
    top, shown = _top(active, verdict, meta)
    sections = [
        ("Summary", _summary(active, verdict, files_analyzed, hidden)),
        ("Risk at a glance", _risk_table(active, len(suppressed), len(verdict.baselined))),
        ("Top findings", top),
        ("Other findings", _others([f for f in active if f.fingerprint not in shown], meta)),
        ("Suppressions and baseline", _set_aside(suppressed, verdict.baselined, meta)),
        ("Method and limits", _method(rules, tool_version, files_analyzed, skipped)),
    ]
    lines = [
        "# Security and reliability review",
        "",
        "An automated review of this repository's code for security and reliability problems, "
        "made with seamscan.",
    ]
    for n, (title, body) in enumerate(sections, start=1):
        lines += ["", f"## {n}. {title}", "", *body]
    return "\n".join(lines) + "\n"
