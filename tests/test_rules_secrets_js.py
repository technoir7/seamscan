"""SC-SEC-001/003 on TS/JS: severity, positions and what gets printed."""

from bench.fake_secrets import FAKES
from seamscan.analysis import analyze
from seamscan.model import Finding, Severity, SourceFile
from seamscan.rules.base import Rule
from seamscan.rules.secrets import PROVIDER_SECRET, RULES, SECRET_FALLBACK

RULE: dict[str, Rule] = {r.meta.id: r for r in RULES}


def run(rule_id: str, files: dict[str, str]) -> tuple[Finding, ...]:
    sources = [SourceFile(path, text) for path, text in files.items()]
    return analyze(sources, rules=[RULE[rule_id]]).findings


# ---------------------------------------------------------------- SC-SEC-001


def test_key_in_browser_code_is_left_to_sec002():
    key = FAKES["FAKE_STRIPE_LIVE"]
    src = f'"use client";\nconst stripe = new Stripe("{key}");\n'
    assert not run(PROVIDER_SECRET.id, {"components/Pay.tsx": src})
    (server,) = run(PROVIDER_SECRET.id, {"app/api/pay/route.ts": src.split("\n", 1)[1]})
    assert server.severity is Severity.CRITICAL


def test_js_test_mode_key_is_low():
    key = FAKES["FAKE_STRIPE_TEST"]
    (f,) = run(PROVIDER_SECRET.id, {"server/pay.js": f"const k = '{key}';\n"})
    assert f.severity is Severity.LOW


def test_js_secret_location_points_at_the_secret_inside_a_template():
    pat = FAKES["FAKE_GITHUB_PAT"]
    src = f"const u = `https://${{user}}:{pat}@github.com/${{repo}}`;\n"
    (f,) = run(PROVIDER_SECRET.id, {"scripts/push.mjs": src})
    loc = f.location
    start = src.index(pat) + 1
    assert (loc.start_line, loc.start_col, loc.end_line, loc.end_col) == (
        1,
        start,
        1,
        start + len(pat),
    )


def test_js_secret_output_is_redacted():
    key = FAKES["FAKE_ANTHROPIC"]
    (f,) = run(PROVIDER_SECRET.id, {"server/ai.ts": f'export const k = "{key}";\n'})
    assert key not in f.message and key not in f.evidence
    assert "…" in f.evidence


def test_js_test_files_and_comments_are_out_of_scope():
    key = FAKES["FAKE_STRIPE_LIVE"]
    files = {
        "lib/pay.test.ts": f'const k = "{key}";\n',
        "src/__tests__/pay.tsx": f'const k = "{key}";\n',
        "lib/pay.ts": f"// {key}\nexport {{}};\n",
    }
    assert not run(PROVIDER_SECRET.id, files)


# ---------------------------------------------------------------- SC-SEC-003


def lines(files: dict[str, str]) -> list[int]:
    return [f.location.start_line for f in run(SECRET_FALLBACK.id, files)]


def test_js_fallback_forms():
    src = (
        'const a = process.env.JWT_SECRET || "dev";\n'
        "const b = process.env.API_KEY ?? `dev`;\n"
        'const c = process.env["SESSION_SECRET"] ?? "dev";\n'
        'const d = import.meta.env.VITE_API_KEY ?? "dev";\n'
        'const e = Deno.env.get("WEBHOOK_SECRET") ?? "dev";\n'
        'const f = opts.token ?? process.env.CRON_TOKEN ?? "dev";\n'
        'const { AUTH_PASSWORD = "admin", PORT = "3000" } = process.env;\n'
        'const { ADMIN_TOKEN: admin = "x" } = process.env;\n'
    )
    # Line 4 reads VITE_API_KEY: bundled into the browser, so not a fallback secret.
    assert lines({"server/config.ts": src}) == [1, 2, 3, 5, 6, 7, 8]


def test_js_fallbacks_for_other_services_credentials_fail_closed():
    src = (
        'const a = process.env.DATABASE_PASSWORD ?? "postgres";\n'
        'const { REDIS_PASSWORD = "redis" } = process.env;\n'
        'const c = process.env.GITHUB_TOKEN ?? process.env.SESSION_SECRET ?? "dev";\n'
        'const d = process.env.STRIPE_WEBHOOK_SECRET || "dev";\n'
    )
    # Line 3's chain is named after its first secret the app holds, SESSION_SECRET.
    findings = run(SECRET_FALLBACK.id, {"server/config.ts": src})
    assert [f.location.start_line for f in findings] == [3, 4]
    assert "SESSION_SECRET" in findings[0].message


def test_js_fallback_resolves_imported_env():
    src = 'import { env } from "node:process";\nconst s = env.JWT_SECRET || "dev";\n'
    assert lines({"server/config.mjs": src}) == [2]


def test_js_fallback_exclusions():
    src = (
        'const a = process.env.JWT_ALGORITHM ?? "HS256";\n'
        'const b = process.env.JWT_SECRET ?? "";\n'
        "const c = process.env.JWT_SECRET ?? `${x}`;\n"
        'const d = process.env.SSL_KEY ?? "/etc/ssl/server.key";\n'
        'const e = import.meta.env.VITE_SUPABASE_ANON_KEY ?? "x";\n'
        'const f = process.env.JWT_SECRET && "x";\n'
        'const g = config.JWT_SECRET ?? "x";\n'
        'const h = Deno.env.get(name) ?? "x";\n'
        'const { JWT_SECRET = "x" } = settings;\n'
    )
    assert lines({"server/config.ts": src}) == []


def test_js_fallback_chain_with_two_literals_is_reported_once():
    src = 'const a = process.env.JWT_SECRET || "one" || "two";\n'
    assert lines({"server/config.js": src}) == [1]


def test_js_fallback_skips_test_files_and_hides_the_default():
    src = 'const s = process.env.SESSION_SECRET || "hunter2-prod";\n'
    assert not run(SECRET_FALLBACK.id, {"src/auth.test.ts": src})
    (f,) = run(SECRET_FALLBACK.id, {"server/auth.ts": src})
    assert "SESSION_SECRET" in f.message
    assert "hunter2" not in f.message + f.evidence
