"""SC-CODE-002/003/004/009/010 details the benchmark cases don't pin down: severity,
evidence redaction, de-duplication and edge cases of the helpers."""

from seamscan.analysis import analyze
from seamscan.model import Finding, Severity, SourceFile
from seamscan.rules.base import Rule
from seamscan.rules.code import (
    HARDCODED_CREDENTIAL,
    RULES,
    SWALLOWED_EXCEPTION,
    UNFINISHED_CODE,
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


# ---------------------------------------------------------------- SC-CODE-003


def test_not_implemented_at_module_level_and_in_concrete_class():
    src = (
        "raise NotImplementedError\n"
        "class Exporter:\n"
        "    def export(self):\n"
        "        raise NotImplementedError('pdf')\n"
    )
    assert lines(run(UNFINISHED_CODE.id, src)) == [1, 4]


def test_abcmeta_metaclass_and_protocol_generic_are_interfaces():
    src = (
        "import abc\n"
        "from typing import Protocol, TypeVar\n"
        "T = TypeVar('T')\n"
        "class Store(metaclass=abc.ABCMeta):\n"
        "    def save(self):\n"
        "        raise NotImplementedError\n"
        "class Checker(Protocol[T]):\n"
        "    def check(self, item: T) -> bool:\n"
        "        return True\n"
    )
    assert run(UNFINISHED_CODE.id, src) == []


def test_guard_names_match_whole_words_only():
    src = (
        "def get_author(): pass\n"
        "def authorize(user): pass\n"
        "def is_verified(user):\n"
        "    '''Docstring only.'''\n"
        "def checkout(cart): pass\n"
    )
    assert lines(run(UNFINISHED_CODE.id, src)) == [2, 3]


def test_guard_with_real_logic_or_return_false_is_fine():
    src = "def verify(sig):\n    return False\ndef check(x):\n    return x > 0\n"
    assert run(UNFINISHED_CODE.id, src) == []


# ---------------------------------------------------------------- SC-CODE-004


def test_literal_is_redacted_in_evidence():
    src = 'def login(password):\n    return password == "correct-horse-battery"\n'
    [f] = run(HARDCODED_CREDENTIAL.id, src)
    assert "correct-horse-battery" not in f.evidence
    assert "password ==" in f.evidence


def test_is_and_bytes_and_from_imported_compare_digest():
    src = (
        "from secrets import compare_digest\n"
        "def a(token):\n"
        "    return token is 'abc123'\n"
        "def b(secret):\n"
        "    return secret != b'k3y'\n"
        "def c(sig):\n"
        "    return compare_digest(sig, 'deadbeef')\n"
    )
    assert lines(run(HARDCODED_CREDENTIAL.id, src)) == [3, 5, 7]


def test_rejection_polarity():
    src = (
        "def a(api_key):\n"
        "    if api_key == 'change-me':\n"
        "        raise SystemExit('set API_KEY')\n"
        "def b(api_key):\n"
        "    if api_key != 'change-me':\n"
        "        raise PermissionError\n"
        "def c(api_key):\n"
        "    if api_key == 'change-me':\n"
        "        return grant()\n"
    )
    assert lines(run(HARDCODED_CREDENTIAL.id, src)) == [5, 8]


def test_only_a_loop_variable_named_token_is_exempt():
    src = (
        "def parse(tokens, token):\n"
        "    for t in tokens:\n"
        "        pass\n"
        "    return token == 'letmein'\n"
    )
    assert lines(run(HARDCODED_CREDENTIAL.id, src)) == [4]
