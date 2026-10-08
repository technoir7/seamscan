import json

from seamscan.facts.project import PackageKind, build_project
from seamscan.facts.roles import Role
from seamscan.model import SourceFile


def pkg(deps: dict[str, str], dev: dict[str, str] | None = None) -> str:
    return json.dumps({"name": "x", "dependencies": deps, "devDependencies": dev or {}})


def test_package_kinds():
    project = build_project(
        [
            SourceFile("web/package.json", pkg({"react": "19"}, {"vite": "7"})),
            SourceFile("api/package.json", pkg({"express": "5"})),
            SourceFile("site/package.json", pkg({"next": "16", "react": "19"})),
            SourceFile("tools/package.json", pkg({"chalk": "5"})),
        ]
    )
    kinds = {p.dir: p.kind for p in project.packages}
    assert kinds == {
        "web": PackageKind.FRONTEND,
        "api": PackageKind.BACKEND,
        "site": PackageKind.NEXT,
        "tools": PackageKind.UNKNOWN,
    }


def test_src_of_a_node_backend_is_server_code():
    project = build_project(
        [SourceFile("package.json", pkg({"express": "5", "pg": "8"})), SourceFile("src/app.ts", "")]
    )
    assert project.role("src/app.ts") is Role.SERVER


def test_src_of_a_vite_app_is_client_code():
    project = build_project([SourceFile("package.json", pkg({"react": "19"}, {"vite": "7"}))])
    assert project.role("src/App.tsx") is Role.CLIENT
    assert project.role("src/server/api.ts") is Role.SERVER


def test_next_src_directory_layout():
    project = build_project([SourceFile("package.json", pkg({"next": "16"}))])
    assert project.role("src/app/api/messages/route.ts") is Role.SERVER
    assert project.role("src/app/dashboard/page.tsx") is Role.SERVER
    assert project.role("src/components/Chat.tsx", "use client") is Role.CLIENT
    assert project.role("src/middleware.ts") is Role.SERVER


def test_monorepo_paths_are_judged_relative_to_their_package():
    project = build_project(
        [
            SourceFile("apps/web/package.json", pkg({"next": "16"})),
            SourceFile("apps/api/package.json", pkg({"hono": "4"})),
        ]
    )
    assert project.role("apps/web/app/api/x/route.ts") is Role.SERVER
    assert project.role("apps/api/src/index.ts") is Role.SERVER
    assert project.role("apps/web/app/x.test.ts") is Role.TEST


def test_no_package_json_keeps_the_path_rules():
    project = build_project([])
    assert project.role("src/App.tsx") is Role.CLIENT
    assert project.role("app/api/x/route.ts") is Role.SERVER
    assert project.role("worker.py") is Role.SERVER


def test_supabase_table_references_are_indexed_with_roles():
    project = build_project(
        [
            SourceFile("package.json", pkg({"react": "19"}, {"vite": "7"})),
            SourceFile(
                "src/pages/Chat.tsx",
                "const { data } = await supabase\n  .from('messages')\n  .select('*');\n",
            ),
            SourceFile(
                "supabase/functions/x/index.ts", 'await admin.from("audit_log").insert(r);\n'
            ),
        ]
    )
    (ref,) = project.table_references["messages"]
    assert (ref.location.path, ref.location.start_line, ref.role) == (
        "src/pages/Chat.tsx",
        2,
        Role.CLIENT,
    )
    assert project.table_references["audit_log"][0].role is Role.SERVER


def test_env_entries_from_every_env_file():
    project = build_project(
        [
            SourceFile(".env.local", "NEXT_PUBLIC_SUPABASE_URL=https://x.supabase.co\nA=1\n"),
            SourceFile("README.md", "A=2\n"),
        ]
    )
    assert [(e.path, e.key, e.line) for e in project.env] == [
        (".env.local", "NEXT_PUBLIC_SUPABASE_URL", 1),
        (".env.local", "A", 2),
    ]


def test_scan_mode_project_facts_include_unchanged_context_files():
    from seamscan.analysis import analyze
    from seamscan.model import WHOLE_FILE, ChangeSet, Confidence, Finding, Severity
    from seamscan.rules.base import Rule, RuleContext, meta

    seen: list[Role] = []

    def probe(ctx: RuleContext) -> list[Finding]:
        seen.extend(ctx.project.js_role(m) for m in ctx.js)
        return []

    rule = Rule(
        meta("SC-META-999", "probe", Severity.LOW, Confidence.LOW, (), frozenset(), ""), probe
    )
    changed = SourceFile("src/index.ts", "export const x = 1;\n")
    manifest = SourceFile("package.json", pkg({"express": "5"}))
    analyze(
        [changed],
        change=ChangeSet(added={"src/index.ts": (WHOLE_FILE,)}),
        rules=[rule],
        context=[changed, manifest],
    )
    assert seen == [Role.SERVER]  # judged by the unchanged package.json, not as browser code


def test_expo_router_app_directory_is_client_code():
    project = build_project([SourceFile("package.json", pkg({"expo": "54", "expo-router": "6"}))])
    assert project.role("app/(tabs)/index.tsx") is Role.CLIENT
    assert project.role("app/_layout.tsx") is Role.CLIENT


def test_next_conventions_still_apply_without_a_package_json():
    project = build_project([])
    assert project.role("app/api/x/route.ts") is Role.SERVER


def test_scan_mode_fingerprints_match_audit_fingerprints():
    # A baseline written by `audit` must still match in `scan` (spec §9.3), so the
    # occurrence index in a fingerprint can't depend on which findings are in scope.
    from seamscan.analysis import analyze
    from seamscan.model import ChangeSet

    text = "import requests\nrequests.get(u, verify=False)\nrequests.get(u, verify=False)\n"
    f = SourceFile("a.py", text)
    audit = analyze([f]).findings
    scan = analyze([f], change=ChangeSet(added={"a.py": ((3, 3),)})).findings
    assert [x.fingerprint for x in scan] == [audit[1].fingerprint]
