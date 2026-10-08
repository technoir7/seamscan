"""SC-SUPA rules (spec §7.2): what the replayed migrations leave open to the Supabase API.

Every rule reads `ctx.project.supabase`, the schema replayed from all migrations, so that
in scan mode a finding in an unchanged migration can still surface through a changed
related location (ADR-002). Only the `public` schema is treated as exposed: it is the one
Supabase serves through PostgREST by default.
"""

from __future__ import annotations

from collections.abc import Iterator

from seamscan.facts.roles import Role
from seamscan.facts.supabase import API_ROLES, Policy, SupabaseSchema, Table, is_literally_true
from seamscan.model import Confidence, Finding, Severity
from seamscan.rules.base import Rule, RuleContext, finding, meta

EXPOSED_SCHEMA = "public"

RLS_MISSING = meta(
    "SC-SUPA-001",
    "Public table without row-level security",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-284",),
    frozenset({"sql"}),
    "A table in the public schema has row-level security off, so anyone holding the "
    "project's public anon key can read and change every row.",
)

OPEN_POLICY = meta(
    "SC-SUPA-002",
    "Policy allows everyone",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-284",),
    frozenset({"sql"}),
    "A row-level security policy uses `true` as its condition, so it applies to every row "
    "for every user it names.",
)

UNSAFE_DEFINER = meta(
    "SC-SUPA-003",
    "Unsafe definer objects",
    Severity.MEDIUM,
    Confidence.HIGH,
    ("CWE-269",),
    frozenset({"sql"}),
    "A SECURITY DEFINER function without a fixed search_path, or a view without "
    "security_invoker over an RLS table, runs with its owner's rights and can bypass RLS.",
)

RLS_DISABLED = meta(
    "SC-SUPA-004",
    "RLS explicitly disabled",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-284",),
    frozenset({"sql"}),
    "A migration turns row-level security off for a public table and nothing turns it back on.",
)


def _qualified(schema: str, name: str) -> str:
    return f"{schema}.{name}"


def _hidden_from_api(table: Table | None) -> bool:
    return table is not None and API_ROLES <= table.revoked_from


# ---------------------------------------------------------------- SC-SUPA-001


def _check_rls_missing(ctx: RuleContext) -> Iterator[Finding]:
    for schema in ctx.project.supabase:
        for table in schema.tables:
            if table.schema != EXPOSED_SCHEMA or table.rls or _hidden_from_api(table):
                continue
            name = _qualified(table.schema, table.name)
            # The lexical index can't see which Supabase project a call targets, so with
            # several migrations directories a call to a same-named table links to each.
            clients = tuple(
                r.location
                for r in ctx.project.table_references.get(table.name, ())
                if r.role is Role.CLIENT
            )
            if clients:
                first = clients[0]
                message = (
                    f"Table {name} has row-level security off and browser code queries it "
                    f"({first.path}:{first.start_line}): anyone with the public anon key can "
                    "read and change every row (the CVE-2025-48757 pattern)"
                )
            else:
                message = (
                    f"Table {name} has row-level security off: anyone with the project's "
                    "public anon key can read and change every row through the API"
                )
            yield finding(
                RLS_MISSING,
                table.created,
                message,
                f"create table {name}",
                severity=Severity.CRITICAL if clients else None,
                related=clients,
            )


# ---------------------------------------------------------------- SC-SUPA-002

_EVERYONE = frozenset({"anon", "public"})
_VERBS = {
    "insert": "insert",
    "update": "update",
    "delete": "delete",
    "all": "read, insert, update and delete",
}


def _policy_evidence(p: Policy) -> str:
    parts = [f'create policy "{p.name}" on {_qualified(p.schema, p.table)}', f"for {p.command}"]
    parts.append("to " + ", ".join(p.roles))
    if p.using is not None:
        parts.append(f"using ({p.using})")
    if p.with_check is not None:
        parts.append(f"with check ({p.with_check})")
    return " ".join(parts)


def _check_open_policy(ctx: RuleContext) -> Iterator[Finding]:
    for schema in ctx.project.supabase:
        for p in schema.policies:
            roles = set(p.roles)
            # A restrictive policy only narrows what permissive ones allow, and other roles
            # (service_role, custom roles) aren't what the public API runs as.
            if not p.permissive or not roles & (_EVERYONE | {"authenticated"}):
                continue
            using_true = p.using is not None and is_literally_true(p.using)
            check_true = p.with_check is not None and is_literally_true(p.with_check)
            who = "anyone, signed in or not," if roles & _EVERYONE else "any signed-in user"
            table = _qualified(p.schema, p.table)
            evidence = _policy_evidence(p)
            if p.command == "select":
                if using_true:
                    yield finding(
                        OPEN_POLICY,
                        p.location,
                        f'Policy "{p.name}" lets {who} read every row of {table}; fine for '
                        "public data, a leak for anything else",
                        evidence,
                        severity=Severity.LOW,
                    )
                continue
            # UPDATE/DELETE pick their rows with USING; INSERT checks new rows with WITH
            # CHECK. An UPDATE whose USING has a row condition and whose WITH CHECK is
            # `true` only lets owners rewrite their own rows, so it isn't reported.
            open_rows = using_true and p.command in ("update", "delete", "all")
            open_inserts = check_true and p.command in ("insert", "all")
            if open_rows or open_inserts:
                clause = "USING (true)" if open_rows else "WITH CHECK (true)"
                yield finding(
                    OPEN_POLICY,
                    p.location,
                    f'Policy "{p.name}" lets {who} {_VERBS.get(p.command, p.command)} any '
                    f"row of {table}: {clause} has no row condition",
                    evidence,
                )


# ---------------------------------------------------------------- SC-SUPA-003


def _rls_tables(schema: SupabaseSchema) -> set[tuple[str, str]]:
    return {(t.schema, t.name) for t in schema.tables if t.rls}


def _check_unsafe_definer(ctx: RuleContext) -> Iterator[Finding]:
    for schema in ctx.project.supabase:
        for f in schema.definer_functions:
            if f.schema != EXPOSED_SCHEMA or f.search_path_set:
                continue
            name = _qualified(f.schema, f.name)
            yield finding(
                UNSAFE_DEFINER,
                f.location,
                f"SECURITY DEFINER function {name} runs as its owner without a fixed "
                "search_path, so objects a caller puts earlier on the path can hijack it; "
                "add `set search_path = ''`",
                f"create function {name} security definer",
            )
        protected = _rls_tables(schema)
        for v in schema.views:
            if v.schema != EXPOSED_SCHEMA or v.security_invoker:
                continue
            bypassed = sorted(v.reads & protected)
            if not bypassed:
                continue
            name = _qualified(v.schema, v.name)
            tables = ", ".join(_qualified(*t) for t in bypassed)
            yield finding(
                UNSAFE_DEFINER,
                v.location,
                f"View {name} runs with its owner's rights, so reading it bypasses "
                f"row-level security on {tables}; create it with (security_invoker = true)",
                f"create view {name}",
            )


# ---------------------------------------------------------------- SC-SUPA-004


def _check_rls_disabled(ctx: RuleContext) -> Iterator[Finding]:
    for schema in ctx.project.supabase:
        for d in schema.rls_disabled:
            if d.schema != EXPOSED_SCHEMA or _hidden_from_api(schema.table(d.schema, d.table)):
                continue
            name = _qualified(d.schema, d.table)
            yield finding(
                RLS_DISABLED,
                d.location,
                f"Row-level security is turned off for {name} and no later migration turns "
                "it back on: anyone with the public anon key can read and change every row",
                f"alter table {name} disable row level security",
            )


RULES: tuple[Rule, ...] = (
    Rule(RLS_MISSING, _check_rls_missing),
    Rule(OPEN_POLICY, _check_open_policy),
    Rule(UNSAFE_DEFINER, _check_unsafe_definer),
    Rule(RLS_DISABLED, _check_rls_disabled),
)
