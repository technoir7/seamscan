from pathlib import Path

from bench.case import Case
from bench.compare import Coverage, ToolFinding, by_category, coverage
from bench.score import Expected


def _case(expected=(), forbidden=()) -> Case:
    return Case("c", "d", "audit", "independent", tuple(expected), tuple(forbidden), "x", Path())


def test_a_hit_needs_a_mapped_rule_at_the_expected_place():
    case = _case([Expected("SC-CODE-007", "a.py", 10, 2)])
    near = ToolFinding("a.py", 11, frozenset({"SC-CODE-007"}))
    elsewhere = ToolFinding("b.py", 10, frozenset({"SC-CODE-007"}))
    unrelated = ToolFinding("a.py", 10, frozenset({"SC-CODE-006"}))
    assert coverage(case, [near])["SC-CODE-007"] == Coverage(1, 1, 0, 0)
    assert coverage(case, [elsewhere, unrelated])["SC-CODE-007"] == Coverage(1, 0, 0, 0)


def test_a_negative_case_alarms_on_any_finding_mapped_to_its_rule():
    case = _case(forbidden=["SC-SEC-001"])
    assert coverage(case, [ToolFinding("x.ts", 3, frozenset({"SC-SEC-001", "SC-SEC-004"}))]) == {
        "SC-SEC-001": Coverage(0, 0, 1, 1)
    }
    assert coverage(case, [])["SC-SEC-001"] == Coverage(0, 0, 1, 0)


def test_rules_roll_up_into_categories():
    rows = by_category({"SC-CODE-001": Coverage(4, 3, 2, 1), "SC-CODE-007": Coverage(6, 3, 0, 0)})
    assert rows == {
        "Risky code patterns": {
            "positives": 10,
            "found": 6,
            "coverage": 0.6,
            "negatives": 2,
            "false_alarms": 1,
        }
    }
