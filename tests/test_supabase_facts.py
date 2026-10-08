"""Supabase schema replay (spec §5.7): a fold over migrations in filename order."""

from pathlib import Path

from seamscan.facts.project import build_project
from seamscan.facts.supabase import SupabaseSchema, build_supabase_schemas, is_literally_true
from seamscan.model import SourceFile

SPIKE = Path(__file__).parent / "fixtures" / "sql" / "supabase_spike.sql"


def replay(*migrations: str) -> SupabaseSchema:
    files = [
        SourceFile(f"supabase/migrations/2026010{i}000000_m{i}.sql", sql)
        for i, sql in enumerate(migrations, start=1)
    ]
    (schema,) = build_supabase_schemas(files)
    return schema


def rls(schema: SupabaseSchema, name: str, namespace: str = "public") -> bool | None:
    table = schema.table(namespace, name)
    return None if table is None else table.rls


# ---------------------------------------------------------------- tables and RLS


def test_tables_default_to_public_without_rls_until_enabled_later():
    schema = replay(
        "create table messages (id int); create table private.jobs (id int);",
        "alter table public.messages enable row level security;",
    )
    assert rls(schema, "messages") is True
    assert rls(schema, "jobs", "private") is False
    created = schema.table("public", "messages")
    assert created is not None
    assert (created.created.path, created.created.start_line) == (
        "supabase/migrations/20260101000000_m1.sql",
        1,
    )


def test_identifiers_fold_unless_quoted():
    schema = replay(
        'CREATE TABLE Public.Bookings (id int); CREATE TABLE "public"."Leads" (id int);',
        "ALTER TABLE IF EXISTS ONLY PUBLIC.BOOKINGS ENABLE ROW LEVEL SECURITY;"
        'alter table "public"."Leads" enable row level security;'
        "alter table public.leads disable row level security;",  # a different table
    )
    assert rls(schema, "bookings") is True
    assert rls(schema, "Leads") is True


def test_create_if_not_exists_keeps_the_existing_table():
    schema = replay(
        "create table t (id int); alter table t enable row level security;",
        "create table if not exists t (id int, extra text);",
    )
    assert rls(schema, "t") is True


def test_drop_and_recreate_starts_over():
    schema = replay(
        "create table t (id int); alter table t enable row level security;"
        "create policy p on t for select using (true);",
        "drop table if exists public.t, public.other cascade; create table t (id int);",
    )
    assert rls(schema, "t") is False
    assert schema.policies == ()


def test_rename_and_set_schema_carry_rls_and_policies():
    schema = replay(
        "create table a (id int); alter table a enable row level security;"
        "create policy p on a for select using (true);",
        "alter table public.a rename to b; create table c (id int);",
        "alter table c set schema private;",
    )
    assert schema.table("public", "a") is None
    assert rls(schema, "b") is True
    assert [p.table for p in schema.policies] == ["b"]
    assert rls(schema, "c", "private") is False
    assert schema.table("public", "c") is None


def test_force_alone_does_not_enable_rls():
    schema = replay(
        "create table t (id int); alter table t force row level security;"
        "create table u (id int);"
        "alter table u enable row level security, force row level security;"
        "alter table u no force row level security;"
    )
    t, u = schema.table("public", "t"), schema.table("public", "u")
    assert t is not None and (t.rls, t.forced) == (False, True)
    assert u is not None and (u.rls, u.forced) == (True, False)


def test_rls_actions_in_a_multi_action_alter_table():
    schema = replay(
        "create table t (id int); alter table t enable row level security;",
        "alter table t add column x text default 'disable row level security',"
        " alter column id set not null, disable row level security;",
    )
    assert rls(schema, "t") is False


def test_rls_text_in_comments_and_strings_is_ignored():
    schema = replay(
        "create table t (id int);"
        "-- alter table t enable row level security;\n"
        "comment on table t is 'alter table t enable row level security';"
        "/* alter table t enable row level security; */"
    )
    assert rls(schema, "t") is False


# ---------------------------------------------------------------- RLS disabled


def test_a_disable_stands_until_reenabled_or_dropped():
    schema = replay(
        "create table a (id int); create table b (id int); create table c (id int);",
        "alter table a disable row level security; alter table b disable row level security;"
        "alter table c disable row level security; alter table ghost disable row level security;",
        "alter table b enable row level security; drop table c;",
        "alter table a enable row level security; alter table a disable row level security;",
    )
    standing = {(d.table, d.location.path[-6:], d.location.start_line) for d in schema.rls_disabled}
    assert standing == {("a", "m4.sql", 1), ("ghost", "m2.sql", 1)}


def test_a_disable_follows_a_rename():
    schema = replay(
        "create table a (id int); alter table a disable row level security;",
        "alter table a rename to b;",
    )
    assert [d.table for d in schema.rls_disabled] == ["b"]


# ---------------------------------------------------------------- policies


def test_policies_from_the_spike_fixture():
    (schema,) = build_supabase_schemas(
        [SourceFile("supabase/migrations/20260101000000_spike.sql", SPIKE.read_text())]
    )
    by_name = {p.name: p for p in schema.policies}
    # "Public profiles are viewable by everyone." is dropped near the end.
    assert set(by_name) == {"Users can update own profile.", "anyone can insert"}
    update = by_name["Users can update own profile."]
    assert (update.schema, update.table, update.command) == ("public", "profiles", "update")
    assert update.roles == ("authenticated",)
    assert update.using == "(select auth.uid()) = id"
    assert update.with_check == "auth.uid() = id"
    assert update.permissive
    insert = by_name["anyone can insert"]
    assert (insert.command, insert.roles, insert.using, insert.with_check) == (
        "insert",
        ("anon",),
        None,
        "true",
    )
    messages = schema.table("public", "messages")
    assert messages is not None and (messages.rls, messages.forced) == (False, True)
    assert rls(schema, "profiles") is True


def test_policy_defaults_and_restrictive():
    schema = replay(
        "create table t (id int);"
        'create policy "p" on t using (true);'
        'create policy q on public.t as restrictive for all to anon, "Authenticated" using (x);'
    )
    p, q = schema.policies
    assert (p.command, p.roles, p.permissive) == ("all", ("public",), True)
    assert (q.roles, q.permissive) == (("anon", "Authenticated"), False)


def test_alter_policy_updates_expressions_and_location():
    schema = replay(
        "create table t (id int);"
        'create policy "own" on t for update to authenticated using (auth.uid() = id);',
        'alter policy "own" on public.t using ( true ) with check (true);',
        'alter policy "own" on t rename to "anyone";',
    )
    (p,) = schema.policies
    assert (p.name, p.using, p.with_check, p.roles) == (
        "anyone",
        "true",
        "true",
        ("authenticated",),
    )
    assert p.location.path.endswith("m2.sql")


def test_literal_true():
    for expr in ("true", " TRUE ", "(true)", "( (True) )", "true /* open */"):
        assert is_literally_true(expr), expr
    for expr in ("auth.uid() = user_id", "is_public = true", "true or false", "'true'", ""):
        assert not is_literally_true(expr), expr


# ---------------------------------------------------------------- functions and views


def test_definer_functions_and_search_path():
    schema = replay(
        "create function public.a() returns int language sql security definer as $$ select 1 $$;"
        "create function b() returns int security definer set search_path = '' as $$ select 1 $$;"
        "create function c() returns int language sql as $$ select 1 $$;"
        "create procedure d() language sql external security definer as $$ select 1 $$;"
        "create function private.e() returns int security definer as 'select 1';",
        "alter procedure d() set search_path to public, extensions;",
    )
    found = {(f.schema, f.name): f.search_path_set for f in schema.definer_functions}
    assert found == {
        ("public", "a"): False,
        ("public", "b"): True,
        ("public", "d"): True,
        ("private", "e"): False,
    }


def test_definer_text_inside_bodies_does_not_count():
    schema = replay(
        "create function f() returns int language plpgsql as $$ begin"
        " -- security definer\n return 1; end $$;"
        "create function g() returns text language sql as 'select ''security definer''';"
    )
    assert schema.definer_functions == ()


def test_functions_are_replaced_dropped_and_switched():
    schema = replay(
        "create function a() returns int security definer as $$ select 1 $$;"
        "create function b() returns int security definer as $$ select 1 $$;"
        "create function c() returns int as $$ select 1 $$;",
        "create or replace function a() returns int security invoker as $$ select 1 $$;"
        "drop function if exists public.b(), x;"
        "alter function c() security definer;",
    )
    assert [(f.name, f.search_path_set) for f in schema.definer_functions] == [("c", False)]


def test_views_record_invoker_option_and_what_they_read():
    schema = replay(
        "create view v1 with (security_invoker = true) as select * from public.t;"
        "create view v2 with (security_invoker) as select * from t;"
        "create view v3 with (security_barrier, security_invoker = off) as select * from t;"
        'create view public.v4 as select a.x from "public"."T" a, w join s.u b on true;'
        "create view v5 as select 1;",
        "alter view v5 set (security_invoker = on); create materialized view m as select 1;",
    )
    views = {v.name: v for v in schema.views}
    assert {n: v.security_invoker for n, v in views.items()} == {
        "v1": True,
        "v2": True,
        "v3": False,
        "v4": False,
        "v5": True,
    }
    assert views["v4"].reads == frozenset({("public", "T"), ("s", "u"), ("public", "w")})


# ---------------------------------------------------------------- grants


def test_grants_to_api_roles_are_recorded_and_revoke_all_hides_a_table():
    schema = replay(
        "create table a (id int); create table b (id int); create table c (id int);"
        "grant select on public.a to anon, authenticated;"
        "grant usage on schema public to postgres;",
        "revoke all on table public.b from anon, authenticated;"
        "revoke all privileges on c from anon, authenticated;"
        "grant select on c to authenticated;",
    )
    assert [(g.privileges, g.roles) for g in schema.grants] == [
        (("select",), ("anon", "authenticated")),
        (("select",), ("authenticated",)),
    ]
    revoked = {t.name: t.revoked_from for t in schema.tables}
    assert revoked == {
        "a": frozenset(),
        "b": frozenset({"anon", "authenticated"}),
        "c": frozenset({"anon"}),
    }


# ---------------------------------------------------------------- files and bookkeeping


def test_migrations_replay_in_filename_order_and_other_sql_is_ignored():
    files = [
        SourceFile(
            "supabase/migrations/20260102_b.sql", "alter table t enable row level security;"
        ),
        SourceFile("supabase/migrations/20260101_a.sql", "create table t (id int);"),
        SourceFile("supabase/seed.sql", "alter table t disable row level security;"),
        SourceFile("supabase/schema.sql", "create table s (id int);"),
        SourceFile("supabase/migrations/notes.md", "create table n (id int);"),
        SourceFile("db/migrations/001.sql", "create table d (id int);"),
    ]
    (schema,) = build_supabase_schemas(files)
    assert schema.directory == "supabase/migrations"
    assert [(t.name, t.rls) for t in schema.tables] == [("t", True)]


def test_each_migrations_directory_is_its_own_database():
    files = [
        SourceFile("apps/a/supabase/migrations/1_x.sql", "create table t (id int);"),
        SourceFile(
            "apps/b/supabase/migrations/1_x.sql",
            "create table t (id int); alter table t enable row level security;",
        ),
    ]
    a, b = build_supabase_schemas(files)
    assert (a.directory, rls(a, "t")) == ("apps/a/supabase/migrations", False)
    assert (b.directory, rls(b, "t")) == ("apps/b/supabase/migrations", True)


def test_unrecognized_statements_are_counted_not_fatal():
    schema = replay(
        "create extension if not exists pgcrypto; create index i on t (x);"
        "insert into t values (1); do $$ begin end $$; create table t (id int); garbage (((;"
    )
    assert (schema.statements, schema.unrecognized) == (6, 5)


def test_project_model_carries_the_schemas_of_context_files_too():
    project = build_project(
        [SourceFile("supabase/migrations/1_init.sql", "create table t (id int);")]
    )
    (schema,) = project.supabase
    assert rls(schema, "t") is False
