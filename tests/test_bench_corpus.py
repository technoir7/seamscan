"""Corpus integrity (spec §8.1, §12.2)."""

import re
from pathlib import Path

from bench.case import CASES_DIR, case_files, expected_split, load_all
from bench.fake_secrets import FAKES
from seamscan.rules.registry import RULES

DOCS = Path(__file__).resolve().parent.parent / "docs" / "rules"
SECRET_SHAPES = re.compile(
    r"sk_live_|rk_live_|sk-proj-|sk-ant-|ghp_[A-Za-z0-9]{20}|AKIA[0-9A-Z]{16}|sb_secret_"
)


def test_every_case_loads_and_its_split_is_hash_derived():
    cases = load_all()
    assert cases
    for case in cases:
        assert case.split == expected_split(case.id), (
            f"{case.id}: split must be {expected_split(case.id)}"
        )


def test_expected_lines_exist_in_the_case_files():
    for case in load_all():
        files = {f.path: f.text for f in case_files(case)}
        for e in case.expected:
            assert e.path in files, f"{case.id}: {e.path} missing"
            assert 1 <= e.line <= len(files[e.path].splitlines()), f"{case.id}: line {e.line}"


def test_case_files_hold_placeholders_not_secret_shaped_strings():
    for path in CASES_DIR.rglob("*"):
        if path.is_file():
            assert not SECRET_SHAPES.search(path.read_text()), (
                f"{path}: use a {{FAKE_*}} placeholder"
            )


def test_fake_secrets_really_are_secret_shaped():
    assert all(
        SECRET_SHAPES.search(v) for k, v in FAKES.items() if "PK_" not in k and "TEST" not in k
    )


def test_every_registered_rule_has_docs_and_enough_cases():
    cases = load_all()
    for rule in RULES:
        rid = rule.meta.id
        assert (DOCS / f"{rid}.md").exists(), f"{rid}: missing docs/rules/{rid}.md"
        positives = sum(any(e.rule == rid for e in c.expected) for c in cases)
        negatives = sum(rid in c.forbidden for c in cases)
        assert positives >= 5 and negatives >= 5, (
            f"{rid}: {positives} positive / {negatives} negative cases"
        )
