"""Corpus integrity (spec §8.1, §12.2)."""

import re
from pathlib import Path

from bench.case import CASES_DIR, case_files, expected_split, load_all
from bench.fake_secrets import FAKES
from seamscan.parse.javascript import js_dialect
from seamscan.rules.registry import RULES

DOCS = Path(__file__).resolve().parent.parent / "docs" / "rules"
SECRET_SHAPES = re.compile(
    r"sk_live_|rk_live_|sk-proj-|sk-ant-|ghp_[A-Za-z0-9]{20}|github_pat_[A-Za-z0-9_]{20}|AKIA[0-9A-Z]{16}"
    r"|sb_secret_|xox[baprs]-[0-9A-Za-z]{6}|eyJ[A-Za-z0-9_-]{10,}\.eyJ"
    # Public keys, but GitHub secret scanning reports these shapes too.
    r"|sb_publishable_[A-Za-z0-9_-]{16}|AIza[0-9A-Za-z_-]{35}"
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


# Languages that need their own cases: a rule that claims TypeScript support must be
# shown to work on TypeScript, not only on Python.
CODE_LANGUAGES = ("python", "javascript")


def language_of(path: str) -> str | None:
    if path.endswith(".py"):
        return "python"
    if js_dialect(path) is not None:
        return "javascript"
    return None


def test_every_registered_rule_has_docs_and_enough_cases_per_language():
    cases = load_all()
    files = {c.id: {language_of(f.path) for f in case_files(c)} for c in cases}
    problems: list[str] = []
    for rule in RULES:
        rid = rule.meta.id
        if not (DOCS / f"{rid}.md").exists():
            problems.append(f"{rid}: missing docs/rules/{rid}.md")
        for lang in (lang for lang in CODE_LANGUAGES if lang in rule.meta.languages):
            positives = sum(
                any(e.rule == rid and language_of(e.path) == lang for e in c.expected)
                for c in cases
            )
            negatives = sum(rid in c.forbidden and lang in files[c.id] for c in cases)
            if positives < 5 or negatives < 5:
                problems.append(f"{rid} [{lang}]: {positives} positive / {negatives} negative")
    assert not problems, "\n".join(problems)


def test_no_case_file_is_hidden_by_gitignore():
    # Cases live on disk while they are written, so a case can pass locally while git
    # silently leaves files out (an unanchored `lib/` once hid 61 TypeScript files).
    import subprocess

    hidden = subprocess.run(
        ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "bench/cases"],
        cwd=CASES_DIR.parent.parent,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert not hidden, f"git ignores these case files: {hidden[:10]}"


def test_readme_rule_table_matches_the_registry():
    readme = (DOCS.parent.parent / "README.md").read_text()
    listed = set(re.findall(r"^\| \[(SC-[A-Z]+-\d{3})\]", readme, flags=re.M))
    assert listed == {r.meta.id for r in RULES}
