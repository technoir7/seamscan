"""The SQL statement scanner (ADR-001): splitting, quoting forms and token normalization."""

from pathlib import Path

import pytest

from seamscan.parse.sql import TokenKind, statements

SPIKE = Path(__file__).parent / "fixtures" / "sql" / "supabase_spike.sql"


def texts(sql: str) -> list[str]:
    return [s.text for s in statements(sql)]


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        ("select 1; select 2;", ["select 1", "select 2"]),
        ("select 1; select 2", ["select 1", "select 2"]),  # no trailing semicolon
        (";; select 1 ;  ;", ["select 1"]),  # empty statements are skipped
        ("insert into t values ('a;b'); select 2", ["insert into t values ('a;b')", "select 2"]),
        ("select 'it''s; fine'; select 2", ["select 'it''s; fine'", "select 2"]),
        ("select E'it\\'s; fine'; select 2", ["select E'it\\'s; fine'", "select 2"]),
        ("select e'a\\\\'; select 2", ["select e'a\\\\'", "select 2"]),
        # Without the E prefix a backslash is an ordinary character.
        ("select 'C:\\'; select 2", ["select 'C:\\'", "select 2"]),
        ('create table "a;b" (x int); select 1', ['create table "a;b" (x int)', "select 1"]),
        ('select "a""b;"; select 1', ['select "a""b;"', "select 1"]),
        ("select $$ a; b $$; select 2", ["select $$ a; b $$", "select 2"]),
        (
            "select $fn$ $$; 'x; $fn$; select 2",
            ["select $fn$ $$; 'x; $fn$", "select 2"],
        ),
        ("prepare p as select $1; select 2", ["prepare p as select $1", "select 2"]),
        ("select a$b; select 2", ["select a$b", "select 2"]),  # $ inside a name
        ("select 1 -- it's; here\n; select 2", ["select 1", "select 2"]),
        ("/* a /* b; */ c; */ select 1; select 2", ["select 1", "select 2"]),
        ("-- $$\nselect 1; select 2", ["select 1", "select 2"]),
        ("select '--', '/*'; select 2", ["select '--', '/*'", "select 2"]),
        ('select "--" from t; select 2', ['select "--" from t', "select 2"]),
    ],
)
def test_splits_on_semicolons_outside_quotes_and_comments(sql: str, expected: list[str]):
    assert texts(sql) == expected


def test_unterminated_quotes_run_to_the_end_without_failing():
    assert texts("select 'abc; select 2") == ["select 'abc; select 2"]
    assert texts("select $$ abc; select 2") == ["select $$ abc; select 2"]
    assert texts("select 1; /* open comment; select 2") == ["select 1"]


def test_statement_position_is_its_first_token_not_a_leading_comment():
    sql = "-- header\n\n/* note */  create table t (\n  id int\n);\n\nselect 1;"
    first, second = statements(sql)
    assert (first.line, first.col, first.end_line) == (3, 13, 5)
    assert first.text == "create table t (\n  id int\n)"
    assert (second.line, second.col) == (7, 1)


def test_tokens_normalize_words_and_unquote_identifiers():
    (stmt,) = statements('ALTER TABLE "Public"."My ""Table""" ENABLE row LEVEL security')
    kinds = [(t.kind, t.text) for t in stmt.tokens]
    assert kinds == [
        (TokenKind.WORD, "alter"),
        (TokenKind.WORD, "table"),
        (TokenKind.QUOTED, "Public"),
        (TokenKind.SYMBOL, "."),
        (TokenKind.QUOTED, 'My "Table"'),
        (TokenKind.WORD, "enable"),
        (TokenKind.WORD, "row"),
        (TokenKind.WORD, "level"),
        (TokenKind.WORD, "security"),
    ]


def test_string_and_dollar_tokens_carry_their_contents():
    (stmt,) = statements("select 'it''s', E'a\\'b', $tag$ body; $tag$, 42")
    values = [(t.kind, t.text) for t in stmt.tokens if t.kind is not TokenKind.SYMBOL]
    assert values == [
        (TokenKind.WORD, "select"),
        (TokenKind.STRING, "it's"),
        (TokenKind.STRING, "a\\'b"),  # escapes are kept as written
        (TokenKind.DOLLAR, " body; "),
        (TokenKind.NUMBER, "42"),
    ]


def test_source_between_tokens_keeps_the_original_text():
    (stmt,) = statements("create policy p on t using (  auth.uid() = user_id  )")
    open_paren = next(i for i, t in enumerate(stmt.tokens) if t.text == "(")
    assert stmt.source(open_paren + 1, len(stmt.tokens) - 2) == "auth.uid() = user_id"


def test_positions_follow_newlines_inside_quotes():
    first, second = statements("select 'a\nb',\n  $$\n$$,\n  x;\n  select 2")
    assert (first.end_line, first.end_col) == (5, 4)
    assert (second.line, second.col) == (6, 3)


def test_the_supabase_spike_fixture():
    found = list(statements(SPIKE.read_text()))
    assert len(found) == 16
    heads = [" ".join(t.text for t in s.tokens[:3]) for s in found]
    assert heads[7] == "create or replace"
    assert found[7].line == 16
    assert found[8].line == 26
    do_block = found[13].tokens  # one statement, despite the semicolons in its body
    assert [t.kind for t in do_block] == [TokenKind.WORD, TokenKind.DOLLAR]
    assert found[-1].text.endswith("with check (true)")
