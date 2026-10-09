"""SQL text -> statements and tokens (ADR-001: a small scanner, not a SQL parser). Pure.

Splits on `;` outside single-quoted strings (including `E'...'`), double-quoted
identifiers, dollar-quoted bodies (`$$`, `$tag$`), `--` comments and nested `/* */`
comments, the way psql does. Each statement keeps its tokens so callers can match
statement heads without being fooled by text inside quotes or comments.

An unterminated quote or comment runs to the end of the text instead of failing:
Postgres would have rejected such a migration, so nothing after it was applied anyway.
"""

from __future__ import annotations

import bisect
import re
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from typing import NamedTuple


class TokenKind(StrEnum):
    WORD = "word"  # unquoted name or keyword, lowercased (Postgres folds them)
    QUOTED = "quoted"  # "double-quoted" name, as written, with "" unescaped
    STRING = "string"  # '...' or E'...' contents: '' unescaped, backslash escapes kept
    DOLLAR = "dollar"  # $tag$...$tag$ body
    NUMBER = "number"
    SYMBOL = "symbol"  # any other single character: ( ) , . = ...


class Token(NamedTuple):  # a tuple, not a dataclass: migrations hold many thousands
    kind: TokenKind
    text: str
    start: int  # offset into the scanned text
    end: int


@dataclass(frozen=True)
class Statement:
    tokens: tuple[Token, ...]  # never empty
    text: str  # source from the first token to the last, without the closing `;`
    start: int  # offset of the first token
    line: int  # 1-based position of the first token (leading comments are skipped)
    col: int
    end_line: int  # position just past the last token, like every Location
    end_col: int

    def source(self, first: int, last: int) -> str:
        """Original text from token `first` through token `last` (indices, inclusive)."""
        return self.text[self.tokens[first].start - self.start : self.tokens[last].end - self.start]


# Leading whitespace, then one alternation tried in order. A letter is [^\W\d]: Postgres allows
# non-ASCII letters in names, and `$` after the first character. The E-string branch
# comes before WORD so that `E'...'` isn't read as the name `e`; it can only match at a
# token start, because WORD consumes whole names.
_TOKEN = re.compile(
    r"""
    \s*(?:
    (?P<semicolon>;)
    |(?P<line_comment>--[^\n]*)
    |(?P<block_comment>/\*)
    |(?P<escape_string>[eE]'[^'\\]*(?:(?:\\.|'')[^'\\]*)*')
    |(?P<string>'[^']*(?:''[^']*)*')
    |(?P<quoted>"[^"]*(?:""[^"]*)*")
    |(?P<dollar>\$(?:[^\W\d]\w*)?\$)
    |(?P<word>[^\W\d][\w$]*)
    |(?P<number>\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)
    |(?P<unterminated>[eE]?'|")
    |(?P<symbol>\S)
    )""",
    re.VERBOSE | re.DOTALL,
)


def _block_comment_end(text: str, i: int) -> int:
    """Offset just past the (possibly nested) block comment opening at text[i]."""
    depth = 0
    n = len(text)
    while i < n:
        if text.startswith("/*", i):
            depth += 1
            i += 2
        elif text.startswith("*/", i):
            depth -= 1
            i += 2
            if depth == 0:
                return i
        else:
            i += 1
    return n


def _tokens(text: str) -> Iterator[Token | None]:
    """Every token in order; None marks a statement-ending `;`."""
    i, n = 0, len(text)
    while i < n:
        m = _TOKEN.match(text, i)
        if m is None:  # only trailing whitespace is left
            return
        kind, end = m.lastgroup, m.end()
        assert kind is not None
        i = m.start(kind)
        if kind == "semicolon":
            yield None
        elif kind == "block_comment":
            end = _block_comment_end(text, i)
        elif kind == "word":
            yield Token(TokenKind.WORD, m.group(kind).lower(), i, end)
        elif kind == "string":
            yield Token(TokenKind.STRING, text[i + 1 : end - 1].replace("''", "'"), i, end)
        elif kind == "escape_string":
            yield Token(TokenKind.STRING, text[i + 2 : end - 1].replace("''", "'"), i, end)
        elif kind == "quoted":
            yield Token(TokenKind.QUOTED, text[i + 1 : end - 1].replace('""', '"'), i, end)
        elif kind == "dollar":
            tag = m.group(kind)
            close = text.find(tag, end)
            body_end = n if close < 0 else close
            body, end = text[end:body_end], (n if close < 0 else close + len(tag))
            yield Token(TokenKind.DOLLAR, body, i, end)
        elif kind == "number":
            yield Token(TokenKind.NUMBER, m.group(kind), i, end)
        elif kind == "unterminated":  # runs to the end, as the module docstring explains
            yield Token(TokenKind.STRING, text[end:], i, n)
            end = n
        elif kind == "symbol":
            yield Token(TokenKind.SYMBOL, m.group(kind), i, end)
        i = end


def tokens(text: str) -> list[Token]:
    """Every token in `text` (a function body, say), without the `;` between statements."""
    return [tok for tok in _tokens(text) if tok is not None]


def statements(text: str) -> Iterator[Statement]:
    """The non-empty statements in `text`, in order."""
    line_starts = [0, *(m.end() for m in re.finditer("\n", text))]

    def position(offset: int) -> tuple[int, int]:
        line = bisect.bisect_right(line_starts, offset)
        return line, offset - line_starts[line - 1] + 1

    def statement(tokens: list[Token]) -> Statement:
        first, last = tokens[0].start, tokens[-1].end
        return Statement(tuple(tokens), text[first:last], first, *position(first), *position(last))

    current: list[Token] = []
    for tok in _tokens(text):
        if tok is not None:
            current.append(tok)
        elif current:
            yield statement(current)
            current = []
    if current:
        yield statement(current)
