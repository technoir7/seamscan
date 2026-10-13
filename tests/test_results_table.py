"""The README's results table is generated from the recorded benchmark and noise study."""

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent


def _script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "results_table", ROOT / "scripts" / "results_table.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tally(tp: int, fp: int, fn: int) -> dict[str, int]:
    return {"tp": tp, "fp": fp, "fn": fn}


LATEST = {
    "independent_cases": 12,
    "splits": {
        "independent": {
            "SC-SEC-001": _tally(3, 1, 0),
            "SC-SEC-002": _tally(1, 0, 1),
            "SC-SUPA-001": _tally(4, 0, 0),
            "SC-META-004": _tally(2, 0, 0),
            "SC-META-001": _tally(9, 9, 9),  # a notice that a file wasn't parsed: not scored
        }
    },
}
WILD = {
    "lines": 12345,
    "per_kloc": 0.41,
    "repos": [{}, {}],
    "triage": {
        "precision": {"sampled": 5, "true": 3, "false": 1, "unclear": 1, "precision": 0.75},
        "blocking_precision": {"sampled": 2, "true": 1, "false": 1, "unclear": 0, "precision": 0.5},
    },
}


def test_rows_add_up_rules_by_category_and_skip_the_notices():
    table = _script().table(LATEST, WILD)
    assert "| Secrets and keys | 4 | 1 | 1 | 0.80 | 0.80 |" in table
    assert "| Supabase | 4 | 0 | 0 | 1.00 | 1.00 |" in table
    assert "| Dependencies | 2 | 0 | 0 | 1.00 | 1.00 |" in table
    assert "| **All** | 10 | 1 | 1 | **0.91** | **0.91** |" in table
    assert "2 public repositories" in table and "12,345 lines" in table
    assert "3 real, 1 false alarms, 1 unclear (precision 0.75)" in table
    assert "1 of 2 were real (0.50)" in table


def test_render_replaces_only_the_text_between_the_markers():
    script = _script()
    readme = f"intro\n{script.START}\nold table\n{script.END}\noutro\n"
    rendered = script.render(readme, LATEST, WILD)
    assert rendered.startswith("intro\n") and rendered.endswith("\noutro\n")
    assert "old table" not in rendered
    assert script.render(rendered, LATEST, WILD) == rendered


def test_the_readme_table_is_up_to_date():
    script = _script()
    readme = script.README.read_text()
    assert script.render(readme, *script.load()) == readme, (
        "README results table is stale: run `uv run python scripts/results_table.py`"
    )
