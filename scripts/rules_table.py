"""Regenerate the README rule table from the registry: `uv run python scripts/rules_table.py`.

The table sits between the `<!-- rules:start -->` and `<!-- rules:end -->` markers. A test
fails when the README is out of date, so the table can't drift from what ships.
"""

from __future__ import annotations

import sys
from pathlib import Path

from seamscan.rules.registry import RULES

README = Path(__file__).resolve().parent.parent / "README.md"
START, END = "<!-- rules:start -->", "<!-- rules:end -->"
LANGUAGES = {
    "python": "Py",
    "javascript": "TS/JS",
    "sql": "SQL",
    "firebase": "Firebase rules",
    "dotenv": "`.env`",
}
# Short qualifiers a reader needs that the rule title doesn't carry.
NOTES = {
    "SC-SUPA-001": " (CRITICAL when browser code reads it)",
    "SC-CODE-010": " (Trojan Source)",
    "SC-TEST-003": " (`scan` only)",
}


def table() -> str:
    rows = [
        "| Rule | What it finds | Languages | Severity | Confidence |",
        "|---|---|---|---|---|",
    ]
    for rule in sorted(RULES, key=lambda r: r.meta.id):
        m = rule.meta
        langs = ", ".join(LANGUAGES[k] for k in LANGUAGES if k in m.languages)
        rows.append(
            f"| [{m.id}](src/seamscan/rules/docs/{m.id}.md) | {m.title}{NOTES.get(m.id, '')} | {langs} "
            f"| {m.severity.name} | {m.confidence.name} |"
        )
    return "\n".join(rows)


def render(readme: str) -> str:
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    return f"{head}{START}\n{table()}\n{END}{tail}"


if __name__ == "__main__":
    README.write_text(render(README.read_text()))
    sys.stdout.write(f"{README.name}: {len(RULES)} rules\n")
