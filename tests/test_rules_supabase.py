"""SC-SUPA rules through the public pipeline: severity, related locations and scan scope.

The benchmark checks rule, path and line; these tests pin what it doesn't score."""

import json

from seamscan.analysis import analyze
from seamscan.model import WHOLE_FILE, ChangeSet, Finding, Severity, SourceFile
from seamscan.rules import supabase

VITE = SourceFile(
    "package.json", json.dumps({"dependencies": {"react": "19"}, "devDependencies": {"vite": "7"}})
)
MIGRATION = SourceFile(
    "supabase/migrations/20260101000000_init.sql",
    "create table public.messages (id int, body text);\n"
    "create table public.rooms (id int);\n"
    "alter table public.rooms enable row level security;\n",
)
CLIENT = SourceFile(
    "src/components/Chat.tsx",
    "import { supabase } from '../lib/supabase';\n"
    "export async function load() {\n"
    "  return supabase.from('messages').select('*');\n"
    "}\n",
)
SERVER = SourceFile(
    "supabase/functions/digest/index.ts",
    "const { data } = await admin.from('messages').select('*');\n",
)


def run(
    files: list[SourceFile],
    change: ChangeSet | None = None,
    context: tuple[SourceFile, ...] | list[SourceFile] = (),
) -> list[Finding]:
    result = analyze(files, change, supabase.RULES, context)
    return [f for f in result.findings if f.rule_id.startswith("SC-SUPA")]


def test_table_without_rls_is_high_on_its_own():
    (f,) = run([VITE, MIGRATION])
    assert (f.rule_id, f.severity, f.location.start_line) == ("SC-SUPA-001", Severity.HIGH, 1)
    assert f.related == ()
    assert "public.messages" in f.message


def test_a_browser_query_raises_it_to_critical_with_the_call_site_related():
    (f,) = run([VITE, MIGRATION, CLIENT, SERVER])
    assert f.severity is Severity.CRITICAL
    assert [(r.path, r.start_line) for r in f.related] == [("src/components/Chat.tsx", 3)]
    assert "src/components/Chat.tsx:3" in f.message


def test_a_server_query_alone_does_not_raise_it():
    (f,) = run([VITE, MIGRATION, SERVER])
    assert (f.severity, f.related) == (Severity.HIGH, ())


def test_scan_of_only_the_client_change_keeps_the_finding_via_context():
    # The CLI analyzes only the changed files and passes the rest of the repo as context.
    change = ChangeSet(added={CLIENT.path: (WHOLE_FILE,)})
    (f,) = run([CLIENT], change=change, context=[VITE, MIGRATION, CLIENT])
    assert (f.location.path, f.severity) == (MIGRATION.path, Severity.CRITICAL)


def test_scan_of_an_unrelated_change_reports_nothing():
    other = SourceFile("src/App.tsx", "export default function App() { return null; }\n")
    change = ChangeSet(added={other.path: (WHOLE_FILE,)})
    assert run([other], change=change, context=[VITE, MIGRATION, CLIENT, other]) == []


def policies(sql: str) -> list[tuple[str, Severity]]:
    files = [
        SourceFile(
            "supabase/migrations/1_p.sql",
            "create table t (id int);alter table t enable row level security;" + sql,
        )
    ]
    return [(f.message.split('"')[1], f.severity) for f in run(files)]


def test_open_policy_severity_by_command_and_role():
    found = policies(
        "create policy r on t for select using (true);"
        "create policy i on t for insert to anon with check (true);"
        "create policy u on t for update to authenticated using (true);"
        "create policy d on t for delete to authenticated using (user_id = auth.uid());"
        "create policy a on t for all to service_role using (true) with check (true);"
        "create policy x on t as restrictive for all to anon using (true);"
        "create policy w on t for update to authenticated using (auth.uid() = id)"
        " with check (true);"
    )
    assert found == [("r", Severity.LOW), ("i", Severity.HIGH), ("u", Severity.HIGH)]


def test_definer_view_needs_an_rls_table_underneath():
    files = [
        SourceFile(
            "supabase/migrations/1_v.sql",
            "create table a (id int); alter table a enable row level security;"
            "create table b (id int); revoke all on b from anon, authenticated;"
            "create view public.over_a as select * from a;"
            "create view public.over_b as select * from b;"
            "create view private.over_a2 as select * from public.a;",
        )
    ]
    assert [(f.rule_id, "over_a" in f.message) for f in run(files)] == [("SC-SUPA-003", True)]


def test_rls_disabled_ignores_tables_the_api_cannot_reach():
    files = [
        SourceFile(
            "supabase/migrations/1_d.sql",
            "create table a (id int); revoke all on table a from anon, authenticated;"
            "alter table a disable row level security;",
        )
    ]
    assert run(files) == []


def test_sql_comments_can_suppress_with_a_reason():
    sql = SourceFile(
        "supabase/migrations/1_w.sql",
        "create table public.waitlist (email text);\n"
        "alter table public.waitlist enable row level security;\n"
        "-- seamscan: ignore-next-line[SC-SUPA-002] reason: public waitlist, insert only\n"
        "create policy w on public.waitlist for insert to anon with check (true);\n",
    )
    result = analyze([sql], rules=supabase.RULES)
    assert result.findings == ()
    assert [f.rule_id for f in result.suppressed] == ["SC-SUPA-002"]


def test_scan_honours_a_suppression_in_an_unchanged_migration():
    suppressed = SourceFile(
        MIGRATION.path,
        "-- seamscan: ignore-next-line[SC-SUPA-001] reason: demo data, no user rows\n"
        + MIGRATION.text,
    )
    change = ChangeSet(added={CLIENT.path: (WHOLE_FILE,)})
    result = analyze([CLIENT], change, supabase.RULES, [VITE, suppressed, CLIENT])
    assert result.findings == ()
    assert [f.rule_id for f in result.suppressed] == ["SC-SUPA-001"]
