"""Supabase schema replay (spec §5.7): migrations -> the database state they leave. Pure.

Each `supabase/migrations/` directory is one database. Its `*.sql` files are applied in
filename order (the CLI's `<timestamp>_name.sql` convention) as a fold over statements.

Only migrations are replayed. `supabase/seed.sql` runs on `supabase db reset` in local
development, never on `db push` to a hosted project, and holds fixture data. A
`schema.sql` dump or the declarative `supabase/schemas/` files describe the same objects
the migrations create, so replaying them too would double-count or contradict them.

Names follow Postgres: unquoted names fold to lowercase, quoted names keep their case,
and an unqualified name is in `public` (Supabase's default search_path for migrations).
Statements the replay doesn't model are counted, never fatal.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, replace

from seamscan.model import Location, SourceFile
from seamscan.parse.sql import Statement, Token, TokenKind, statements

__all__ = [
    "API_ROLES",
    "DefinerFunction",
    "Grant",
    "Policy",
    "RlsDisabled",
    "SupabaseSchema",
    "Table",
    "View",
    "build_supabase_schemas",
    "is_literally_true",
]

API_ROLES = frozenset({"anon", "authenticated"})  # the roles PostgREST requests run as

_MIGRATION = re.compile(r"(?:^|/)supabase/migrations/[^/]+\.sql$")
_NameKey = tuple[str, str]  # (schema, name)


@dataclass(frozen=True)
class Table:
    schema: str
    name: str
    rls: bool
    forced: bool  # FORCE ROW LEVEL SECURITY; has no effect while rls is off
    created: Location  # the CREATE TABLE statement
    # API roles whose privileges were all revoked (and not granted back): requests running
    # as them can't touch the table at all, RLS or not.
    revoked_from: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Policy:
    name: str
    schema: str
    table: str
    command: str  # all | select | insert | update | delete
    roles: tuple[str, ...]  # ("public",) when the policy has no TO clause
    using: str | None  # expression text inside the parentheses, as written
    with_check: str | None
    permissive: bool
    location: Location  # the statement that last set its roles or expressions


@dataclass(frozen=True)
class DefinerFunction:
    schema: str
    name: str
    search_path_set: bool  # SET search_path in the definition or a later ALTER FUNCTION
    location: Location


@dataclass(frozen=True)
class View:
    schema: str
    name: str
    security_invoker: bool
    reads: frozenset[_NameKey]  # tables and views named after FROM / JOIN in its query
    location: Location


@dataclass(frozen=True)
class Grant:
    privileges: tuple[str, ...]  # ("select", "insert") or ("all",)
    target: str  # object kind as written: "table", "schema", "all tables in schema", ...
    names: tuple[_NameKey, ...]
    roles: tuple[str, ...]  # only the API roles it names
    location: Location


@dataclass(frozen=True)
class RlsDisabled:
    """A DISABLE ROW LEVEL SECURITY that still stands: not re-enabled, table not dropped."""

    schema: str
    table: str
    location: Location


@dataclass(frozen=True)
class SupabaseSchema:
    directory: str  # e.g. "supabase/migrations"
    tables: tuple[Table, ...]
    policies: tuple[Policy, ...]
    definer_functions: tuple[DefinerFunction, ...]
    views: tuple[View, ...]
    grants: tuple[Grant, ...]  # GRANTs naming anon or authenticated, in order
    rls_disabled: tuple[RlsDisabled, ...]
    statements: int
    unrecognized: int  # statements the replay doesn't model, for --stats

    def table(self, schema: str, name: str) -> Table | None:
        return next((t for t in self.tables if (t.schema, t.name) == (schema, name)), None)


def is_literally_true(expression: str) -> bool:
    """`true`, any case, any parentheses or comments around it. Nothing cleverer: ADR-001."""
    tokens = [t for s in statements(expression) for t in s.tokens if t.text not in "()"]
    return len(tokens) == 1 and tokens[0].kind is TokenKind.WORD and tokens[0].text == "true"


# ---------------------------------------------------------------- token cursor


class _Cursor:
    def __init__(self, stmt: Statement) -> None:
        self.stmt = stmt
        self.tokens = stmt.tokens
        self.i = 0

    def peek(self, ahead: int = 0) -> Token | None:
        j = self.i + ahead
        return self.tokens[j] if j < len(self.tokens) else None

    def at_end(self) -> bool:
        return self.i >= len(self.tokens)

    def is_word(self, *options: str, ahead: int = 0) -> bool:
        t = self.peek(ahead)
        return t is not None and t.kind is TokenKind.WORD and t.text in options

    def is_symbol(self, symbol: str) -> bool:
        t = self.peek()
        return t is not None and t.kind is TokenKind.SYMBOL and t.text == symbol

    def words(self, *sequence: str) -> bool:
        """Consume the exact word sequence if it comes next."""
        ahead = self.tokens[self.i : self.i + len(sequence)]
        if len(ahead) < len(sequence):
            return False
        for t, w in zip(ahead, sequence, strict=True):
            if t.kind is not TokenKind.WORD or t.text != w:
                return False
        self.i += len(sequence)
        return True

    def identifier(self) -> str | None:
        t = self.peek()
        if t is None or t.kind not in (TokenKind.WORD, TokenKind.QUOTED):
            return None
        self.i += 1
        return t.text

    def name(self) -> _NameKey | None:
        """A possibly qualified name; the schema defaults to public."""
        parts: list[str] = []
        part = self.identifier()
        while part is not None:
            parts.append(part)
            if not self.is_symbol("."):
                break
            self.i += 1
            part = self.identifier()
        if not parts:
            return None
        return (parts[-2] if len(parts) > 1 else "public", parts[-1])

    def names(self) -> list[_NameKey]:
        found: list[_NameKey] = []
        while (n := self.name()) is not None:
            found.append(n)
            if self.is_symbol("("):  # a function's argument list
                self.skip_parens()
            if not self.is_symbol(","):
                break
            self.i += 1
        return found

    def skip_parens(self) -> tuple[int, int] | None:
        """Consume a parenthesized group; return the token range inside it."""
        if not self.is_symbol("("):
            return None
        start, depth = self.i + 1, 0
        while not self.at_end():
            t = self.tokens[self.i]
            self.i += 1
            if t.kind is TokenKind.SYMBOL and t.text == "(":
                depth += 1
            elif t.kind is TokenKind.SYMBOL and t.text == ")":
                depth -= 1
                if depth == 0:
                    return start, self.i - 1
        return start, self.i

    def parenthesized_source(self) -> str | None:
        inner = self.skip_parens()
        if inner is None or inner[0] >= inner[1]:
            return None
        return self.stmt.source(inner[0], inner[1] - 1)

    def top_level(self) -> Iterator[int]:
        """Indices of the remaining tokens outside parentheses (consumes them)."""
        while not self.at_end():
            if self.is_symbol("("):
                self.skip_parens()
                continue
            yield self.i
            self.i += 1


# ---------------------------------------------------------------- the fold


def _truthy(token: Token | None) -> bool:
    # Postgres boolean input: true/yes/on/1 and their unambiguous prefixes.
    if token is None:
        return True  # a bare option name means true
    value = token.text.lower()
    return value in ("1", "on") or any(word.startswith(value) for word in ("true", "yes"))


_NOT_AN_ALIAS = frozenset(
    {"where", "join", "inner", "left", "right", "full", "cross", "natural", "lateral", "on"}
    | {"using", "group", "order", "limit", "offset", "having", "window", "union", "except"}
    | {"intersect", "fetch", "for", "returning", "with"}
)


def _reads(cursor: _Cursor) -> frozenset[_NameKey]:
    """Relations named after FROM / JOIN in a query. Lexical: subqueries are just more
    FROMs, and a CTE name resolves to a public relation that won't exist."""
    found: set[_NameKey] = set()
    tokens = cursor.tokens
    for i, t in enumerate(tokens):
        if t.kind is not TokenKind.WORD or t.text not in ("from", "join"):
            continue
        sub = _Cursor(cursor.stmt)
        sub.i = i + 1
        while (n := sub.name()) is not None:
            found.add(n)
            sub.words("as")
            if (alias := sub.peek()) is not None and alias.kind in (
                TokenKind.WORD,
                TokenKind.QUOTED,
            ):
                if not (alias.kind is TokenKind.WORD and alias.text in _NOT_AN_ALIAS):
                    sub.i += 1
            if not sub.is_symbol(","):
                break
            sub.i += 1
    return frozenset(found)


class _Replay:
    def __init__(self) -> None:
        self.tables: dict[_NameKey, Table] = {}
        self.policies: dict[_NameKey, dict[str, Policy]] = {}  # table -> name -> policy
        self.functions: dict[_NameKey, DefinerFunction] = {}  # every function; definer or not
        self.definer: dict[_NameKey, bool] = {}
        self.views: dict[_NameKey, View] = {}
        self.grants: list[Grant] = []
        self.disabled: dict[_NameKey, Location] = {}
        self.statements = 0
        self.unrecognized = 0

    def apply(self, path: str, stmt: Statement) -> None:
        self.statements += 1
        loc = Location(path, stmt.line, stmt.col, stmt.end_line, stmt.end_col)
        c = _Cursor(stmt)
        handled = False
        if c.words("create"):
            handled = self._create(c, loc)
        elif c.words("alter"):
            handled = self._alter(c, loc)
        elif c.words("drop"):
            handled = self._drop(c)
        elif c.is_word("grant", "revoke"):
            handled = self._grant(c, loc)
        if not handled:
            self.unrecognized += 1

    # ------------------------------------------------------------ create

    def _create(self, c: _Cursor, loc: Location) -> bool:
        c.words("or", "replace")
        modifiers: set[str] = set()
        while c.is_word("global", "local", "temp", "temporary", "unlogged", "recursive"):
            modifiers.add(c.tokens[c.i].text)
            c.i += 1
        if modifiers & {"temp", "temporary"}:
            return False  # gone at the end of the migration's session
        if c.words("table"):
            return self._create_table(c, loc)
        if c.words("policy"):
            return self._create_policy(c, loc)
        if c.is_word("function", "procedure"):
            c.i += 1
            return self._create_function(c, loc)
        if c.words("view"):
            return self._create_view(c, loc)
        return False

    def _create_table(self, c: _Cursor, loc: Location) -> bool:
        if_not_exists = c.words("if", "not", "exists")
        key = c.name()
        if key is None:
            return False
        if if_not_exists and key in self.tables:
            return True
        self._forget_table(key)
        self.tables[key] = Table(key[0], key[1], rls=False, forced=False, created=loc)
        return True

    def _policy_clauses(self, c: _Cursor, policy: Policy, loc: Location) -> Policy:
        """Parse AS / FOR / TO / USING / WITH CHECK, in any order, onto `policy`."""
        while not c.at_end():
            if c.words("as"):
                permissive = not c.is_word("restrictive")
                c.i += 1
                policy = replace(policy, permissive=permissive)
            elif c.words("for"):
                command = c.identifier()
                policy = replace(policy, command=command or policy.command)
            elif c.words("to"):
                roles: list[str] = []
                while (role := c.identifier()) is not None:
                    roles.append(role)
                    if not c.is_symbol(","):
                        break
                    c.i += 1
                policy = replace(policy, roles=tuple(roles), location=loc)
            elif c.words("using"):
                policy = replace(policy, using=c.parenthesized_source(), location=loc)
            elif c.words("with", "check"):
                policy = replace(policy, with_check=c.parenthesized_source(), location=loc)
            else:
                c.i += 1
        return policy

    def _create_policy(self, c: _Cursor, loc: Location) -> bool:
        name = c.identifier()
        if name is None or not c.words("on") or (table := c.name()) is None:
            return False
        blank = Policy(name, table[0], table[1], "all", ("public",), None, None, True, loc)
        self.policies.setdefault(table, {})[name] = self._policy_clauses(c, blank, loc)
        return True

    def _create_function(self, c: _Cursor, loc: Location) -> bool:
        key = c.name()
        if key is None:
            return False
        c.skip_parens()
        definer = search_path = False
        for i in c.top_level():
            t = c.tokens[i]
            if t.kind is not TokenKind.WORD:
                continue
            if t.text == "security" and c.is_word("definer", "invoker", ahead=1):
                definer = c.tokens[i + 1].text == "definer"
            elif t.text == "set" and c.is_word("search_path", ahead=1):
                search_path = True
        self.functions[key] = DefinerFunction(key[0], key[1], search_path, loc)
        self.definer[key] = definer
        return True

    def _view_options(self, c: _Cursor, invoker: bool) -> bool:
        inner = c.skip_parens()
        if inner is None:
            return invoker
        options = _Cursor(c.stmt)
        options.i = inner[0]
        while options.i < inner[1]:
            option = options.identifier()
            value = None
            if options.is_symbol("="):
                options.i += 1
                value = options.peek()
                options.i += 1
            if option == "security_invoker":
                invoker = _truthy(value)
            while options.i < inner[1] and not options.is_symbol(","):
                options.i += 1
            options.i += 1
        return invoker

    def _create_view(self, c: _Cursor, loc: Location) -> bool:
        key = c.name()
        if key is None:
            return False
        c.skip_parens()  # column names
        invoker = self._view_options(c, False) if c.words("with") else False
        self.views[key] = View(key[0], key[1], invoker, _reads(c), loc)
        return True

    # ------------------------------------------------------------ alter

    def _alter(self, c: _Cursor, loc: Location) -> bool:
        if c.words("table"):
            return self._alter_table(c, loc)
        if c.words("policy"):
            return self._alter_policy(c, loc)
        if c.is_word("function", "procedure"):
            c.i += 1
            return self._alter_function(c)
        if c.words("view"):
            return self._alter_view(c)
        return False

    def _alter_table(self, c: _Cursor, loc: Location) -> bool:
        c.words("if", "exists")
        c.words("only")
        key = c.name()
        if key is None:
            return False
        if c.is_symbol("*"):
            c.i += 1
        if c.words("rename", "to"):
            new = c.identifier()
            if new is not None:
                self._move_table(key, (key[0], new))
            return True
        if c.words("set", "schema"):
            new = c.identifier()
            if new is not None:
                self._move_table(key, (new, key[1]))
            return True
        for i in c.top_level():
            self._rls_action(c.tokens, i, key, loc)
        return True

    def _rls_action(self, t: tuple[Token, ...], i: int, key: _NameKey, loc: Location) -> None:
        """Apply `[NO] ENABLE | DISABLE | FORCE ROW LEVEL SECURITY` if it starts at t[i]."""
        if not (
            i + 3 < len(t)
            and t[i].kind is TokenKind.WORD
            and [x.text for x in t[i + 1 : i + 4]] == ["row", "level", "security"]
            and all(x.kind is TokenKind.WORD for x in t[i + 1 : i + 4])
        ):
            return
        action = t[i].text
        no = i > 0 and t[i - 1].kind is TokenKind.WORD and t[i - 1].text == "no"
        table = self.tables.get(key)
        if action == "enable":
            self.disabled.pop(key, None)
            if table is not None:
                self.tables[key] = replace(table, rls=True)
        elif action == "disable":
            self.disabled[key] = loc
            if table is not None:
                self.tables[key] = replace(table, rls=False)
        elif action == "force" and table is not None:
            self.tables[key] = replace(table, forced=not no)

    def _alter_policy(self, c: _Cursor, loc: Location) -> bool:
        name = c.identifier()
        if name is None or not c.words("on") or (table := c.name()) is None:
            return False
        on_table = self.policies.get(table, {})
        policy = on_table.pop(name, None)
        if policy is None:
            return True  # created outside the migrations; nothing to update
        if c.words("rename", "to") and (new := c.identifier()) is not None:
            policy = replace(policy, name=new)
        else:
            policy = self._policy_clauses(c, policy, loc)
        on_table[policy.name] = policy
        return True

    def _alter_function(self, c: _Cursor) -> bool:
        key = c.name()
        if key is None:
            return False
        c.skip_parens()
        function = self.functions.get(key)
        if function is None:
            return True
        if c.words("rename", "to") and (new := c.identifier()) is not None:
            self._move_function(key, (key[0], new))
            return True
        if c.words("set", "schema") and (new := c.identifier()) is not None:
            self._move_function(key, (new, key[1]))
            return True
        for i in c.top_level():
            t = c.tokens[i]
            if t.kind is not TokenKind.WORD:
                continue
            if t.text == "security" and c.is_word("definer", "invoker", ahead=1):
                self.definer[key] = c.tokens[i + 1].text == "definer"
            elif t.text == "set" and c.is_word("search_path", ahead=1):
                function = replace(function, search_path_set=True)
            elif t.text == "reset" and c.is_word("search_path", "all", ahead=1):
                function = replace(function, search_path_set=False)
        self.functions[key] = function
        return True

    def _alter_view(self, c: _Cursor) -> bool:
        c.words("if", "exists")
        key = c.name()
        if key is None:
            return False
        view = self.views.get(key)
        if view is None:
            return True
        if c.words("rename", "to") and (new := c.identifier()) is not None:
            del self.views[key]
            self.views[(key[0], new)] = replace(view, name=new)
        elif c.words("set", "schema") and (new := c.identifier()) is not None:
            del self.views[key]
            self.views[(new, key[1])] = replace(view, schema=new)
        elif c.words("set"):
            self.views[key] = replace(
                view, security_invoker=self._view_options(c, view.security_invoker)
            )
        elif c.words("reset"):
            inner = c.skip_parens()
            if inner and any(t.text == "security_invoker" for t in c.tokens[inner[0] : inner[1]]):
                self.views[key] = replace(view, security_invoker=False)
        return True

    # ------------------------------------------------------------ drop

    def _drop(self, c: _Cursor) -> bool:
        if c.is_word("table", "view", "function", "procedure"):
            kind = c.tokens[c.i].text
            c.i += 1
            c.words("if", "exists")
            for key in c.names():
                if kind == "table":
                    self._forget_table(key)
                    self.views = {k: v for k, v in self.views.items() if key not in v.reads}
                elif kind == "view":
                    self.views.pop(key, None)
                else:
                    self.functions.pop(key, None)
                    self.definer.pop(key, None)
            return True
        if c.words("policy"):
            c.words("if", "exists")
            name = c.identifier()
            if name is None or not c.words("on") or (table := c.name()) is None:
                return False
            self.policies.get(table, {}).pop(name, None)
            return True
        return False

    # ------------------------------------------------------------ grant / revoke

    def _grant(self, c: _Cursor, loc: Location) -> bool:
        granting = c.tokens[c.i].text == "grant"
        c.i += 1
        c.words("grant", "option", "for")
        privileges: list[str] = []
        while not c.at_end() and not c.is_word("on"):
            t = c.tokens[c.i]
            if t.kind is TokenKind.WORD and t.text != "privileges":
                privileges.append(t.text)
            if c.is_symbol("("):  # column list
                c.skip_parens()
            else:
                c.i += 1
        if not c.words("on"):
            return True  # role membership: GRANT role TO role
        target: list[str] = []
        if c.is_word("table", "schema", "function", "procedure", "routine", "sequence"):
            target = [c.tokens[c.i].text]
            c.i += 1
        elif c.is_word("all"):  # ALL TABLES | SEQUENCES | FUNCTIONS ... IN SCHEMA
            while not c.at_end() and not c.is_word("schema"):
                target.append(c.tokens[c.i].text)
                c.i += 1
            if c.words("schema"):
                target.append("schema")
        names = c.names()
        if not c.is_word("to", "from"):
            return False
        c.i += 1
        roles: list[str] = []
        while (role := c.identifier()) is not None:
            roles.append(role)
            if not c.is_symbol(","):
                break
            c.i += 1
        api = tuple(r for r in roles if r in API_ROLES)
        kind = " ".join(target) or "table"
        if kind == "all tables in schema":
            tables = [k for k in self.tables if k[0] in {n[1] for n in names}]
        elif kind == "table":
            tables = names
        else:
            tables = []
        if granting:
            if api:
                self.grants.append(Grant(tuple(privileges), kind, tuple(names), api, loc))
            for key in tables:
                if (table := self.tables.get(key)) is not None:
                    self.tables[key] = replace(table, revoked_from=table.revoked_from - set(api))
        elif privileges == ["all"]:
            for key in tables:
                if (table := self.tables.get(key)) is not None:
                    self.tables[key] = replace(table, revoked_from=table.revoked_from | set(api))
        return True

    # ------------------------------------------------------------ bookkeeping

    def _forget_table(self, key: _NameKey) -> None:
        self.tables.pop(key, None)
        self.disabled.pop(key, None)
        self.policies.pop(key, None)

    def _move_table(self, old: _NameKey, new: _NameKey) -> None:
        if (table := self.tables.pop(old, None)) is not None:
            self.tables[new] = replace(table, schema=new[0], name=new[1])
        if (disabled := self.disabled.pop(old, None)) is not None:
            self.disabled[new] = disabled
        if (moved := self.policies.pop(old, None)) is not None:
            self.policies[new] = {
                n: replace(p, schema=new[0], table=new[1]) for n, p in moved.items()
            }
        # A view refers to the table itself, not its name, so it follows a rename.
        self.views = {
            k: replace(v, reads=(v.reads - {old}) | {new}) if old in v.reads else v
            for k, v in self.views.items()
        }

    def _move_function(self, old: _NameKey, new: _NameKey) -> None:
        function = self.functions.pop(old)
        self.functions[new] = replace(function, schema=new[0], name=new[1])
        self.definer[new] = self.definer.pop(old, False)

    def result(self, directory: str) -> SupabaseSchema:
        return SupabaseSchema(
            directory=directory,
            tables=tuple(self.tables.values()),
            policies=tuple(p for on_table in self.policies.values() for p in on_table.values()),
            definer_functions=tuple(f for k, f in self.functions.items() if self.definer.get(k)),
            views=tuple(self.views.values()),
            grants=tuple(self.grants),
            rls_disabled=tuple(RlsDisabled(k[0], k[1], loc) for k, loc in self.disabled.items()),
            statements=self.statements,
            unrecognized=self.unrecognized,
        )


def build_supabase_schemas(files: Iterable[SourceFile]) -> tuple[SupabaseSchema, ...]:
    """One replayed schema per `supabase/migrations/` directory, ordered by directory."""
    by_directory: dict[str, list[SourceFile]] = {}
    for f in files:
        if _MIGRATION.search(f.path):
            by_directory.setdefault(f.path.rsplit("/", 1)[0], []).append(f)
    schemas: list[SupabaseSchema] = []
    for directory in sorted(by_directory):
        replay = _Replay()
        for f in sorted(by_directory[directory], key=lambda f: f.path.rsplit("/", 1)[1]):
            for stmt in statements(f.text):
                replay.apply(f.path, stmt)
        schemas.append(replay.result(directory))
    return tuple(schemas)
