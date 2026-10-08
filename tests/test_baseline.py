import json

import pytest

from seamscan.model import Confidence, Finding, Location, Severity
from seamscan.policy.baseline import (
    Baseline,
    BaselineError,
    Entry,
    added_since,
    from_findings,
    parse_baseline,
    prune,
    render_baseline,
)


def f(path: str, rule: str, fingerprint: str) -> Finding:
    return Finding(
        rule,
        Severity.HIGH,
        Confidence.HIGH,
        Location(path, 1, 1, 1, 2),
        "m",
        "e",
        fingerprint=fingerprint,
    )


def test_from_findings_keeps_rule_path_and_fingerprint_sorted():
    b = from_findings([f("z.py", "SC-CODE-001", "f2"), f("a.py", "SC-CODE-002", "f1")])
    assert b.entries == (
        Entry("f1", "SC-CODE-002", "a.py"),
        Entry("f2", "SC-CODE-001", "z.py"),
    )
    assert b.fingerprints() == frozenset({"f1", "f2"})


def test_render_is_sorted_stable_and_ends_with_a_newline():
    b = from_findings([f("z.py", "SC-CODE-001", "f2"), f("a.py", "SC-CODE-002", "f1")])
    text = render_baseline(b)
    assert text == (
        "{\n"
        '  "version": 1,\n'
        '  "entries": [\n'
        '    {"fingerprint": "f1", "rule_id": "SC-CODE-002", "path": "a.py"},\n'
        '    {"fingerprint": "f2", "rule_id": "SC-CODE-001", "path": "z.py"}\n'
        "  ]\n"
        "}\n"
    )
    assert json.loads(text)["version"] == 1


def test_render_empty_baseline_is_valid_json():
    text = render_baseline(Baseline(()))
    assert json.loads(text) == {"version": 1, "entries": []}


def test_render_then_parse_round_trips():
    b = from_findings([f("a b/é.py", "SC-CODE-001", "f1"), f("x.py", "SC-SEC-001", "f2")])
    assert parse_baseline(render_baseline(b)) == b


def test_parse_sorts_and_drops_duplicate_entries():
    text = json.dumps(
        {
            "version": 1,
            "entries": [
                {"fingerprint": "f2", "rule_id": "R", "path": "b.py"},
                {"fingerprint": "f1", "rule_id": "R", "path": "a.py"},
                {"fingerprint": "f2", "rule_id": "R", "path": "b.py"},
            ],
        }
    )
    assert parse_baseline(text).entries == (Entry("f1", "R", "a.py"), Entry("f2", "R", "b.py"))


@pytest.mark.parametrize(
    ("text", "complaint"),
    [
        ("{not json", "not valid JSON"),
        ("[]", "JSON object"),
        ('{"entries": []}', "version"),
        ('{"version": 2, "entries": []}', "version 2"),
        ('{"version": true, "entries": []}', "version True"),
        ('{"version": 1}', "entries"),
        ('{"version": 1, "entries": [], "extra": 1}', "extra"),
        ('{"version": 1, "entries": {}}', "entries"),
        ('{"version": 1, "entries": ["x"]}', "entries[0]"),
        ('{"version": 1, "entries": [{"fingerprint": "f", "rule_id": "R"}]}', "entries[0]"),
        (
            '{"version": 1, "entries": [{"fingerprint": "f", "rule_id": "R", "path": 3}]}',
            "entries[0].path",
        ),
        (
            '{"version": 1, "entries": [{"fingerprint": "", "rule_id": "R", "path": "a"}]}',
            "entries[0].fingerprint",
        ),
        (
            '{"version": 1, "entries": '
            '[{"fingerprint": "f", "rule_id": "R", "path": "a", "line": 3}]}',
            "line",
        ),
    ],
)
def test_parse_rejects_bad_input_with_a_clear_message(text: str, complaint: str):
    with pytest.raises(BaselineError) as err:
        parse_baseline(text)
    assert complaint in str(err.value)


def test_prune_drops_entries_no_current_finding_matches():
    b = from_findings([f("a.py", "R", "f1"), f("b.py", "R", "f2")])
    pruned = prune(b, [f("b.py", "R", "f2"), f("c.py", "R", "f3")])
    assert pruned.entries == (Entry("f2", "R", "b.py"),)


def test_added_since_lists_entries_the_older_baseline_lacks():
    old = from_findings([f("a.py", "R", "f1"), f("b.py", "R", "f2")])
    new = from_findings([f("b.py", "R", "f2"), f("c.py", "R", "f3")])
    assert added_since(new, old) == (Entry("f3", "R", "c.py"),)
    assert added_since(old, old) == ()
