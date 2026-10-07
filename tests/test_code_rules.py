"""SC-CODE-002/003/004/009/010 details the benchmark cases don't pin down: severity,
evidence redaction, de-duplication and edge cases of the helpers."""

from seamscan.analysis import analyze
from seamscan.model import Finding, Severity, SourceFile
from seamscan.rules.base import Rule
from seamscan.rules.code import (
    RULES,
    SWALLOWED_EXCEPTION,
    name_words,
)

BOM, RLO, ZWSP = "\ufeff", "\u202e", "\u200b"


def run(rule_id: str, src: str, path: str = "app/m.py") -> list[Finding]:
    rules: list[Rule] = [r for r in RULES if r.meta.id == rule_id]
    found = analyze([SourceFile(path, src)], rules=rules).findings
    return [f for f in found if f.rule_id == rule_id]  # not SC-META-002 for broken files


def lines(findings: list[Finding]) -> list[int]:
    return [f.location.start_line for f in findings]


def test_name_words_split_snake_camel_and_header_names():
    assert name_words("x_api_key") == ("x", "api", "key")
    assert name_words("verifyAPIKey") == ("verify", "api", "key")
    assert name_words("X-Admin-Token") == ("x", "admin", "token")
    assert name_words("send_2fa_code") == ("send", "2fa", "code")


# ---------------------------------------------------------------- SC-CODE-002


def test_swallowed_write_is_high_and_names_the_call():
    src = "def f(db):\n    try:\n        db.session.commit()\n    except Exception:\n        pass\n"
    [f] = run(SWALLOWED_EXCEPTION.id, src)
    assert f.severity is Severity.HIGH
    assert "db.session.commit" in f.message


def test_swallowed_read_stays_medium():
    src = "def f(p):\n    try:\n        return open(p).read()\n    except:\n        return None\n"
    [f] = run(SWALLOWED_EXCEPTION.id, src)
    assert f.severity is Severity.MEDIUM


def test_except_star_and_test_files():
    src = "try:\n    run()\nexcept* Exception:\n    pass\n"
    assert lines(run(SWALLOWED_EXCEPTION.id, src)) == [3]
    assert run(SWALLOWED_EXCEPTION.id, src, path="tests/test_m.py") == []


def test_handler_that_does_anything_else_is_not_silent():
    src = "try:\n    run()\nexcept Exception:\n    cleanup()\n    pass\n"
    assert run(SWALLOWED_EXCEPTION.id, src) == []
