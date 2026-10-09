"""SC-CODE-001/002/003/004/009/010 on TS/JS: severity, evidence, de-duplication and the
edge cases the benchmark cases don't pin down."""

from seamscan.analysis import analyze
from seamscan.model import Finding, Severity, SourceFile
from seamscan.rules.base import Rule
from seamscan.rules.code import (
    HARDCODED_CREDENTIAL,
    INVISIBLE_UNICODE,
    PREDICTABLE_RANDOM,
    RULES,
    SWALLOWED_EXCEPTION,
    TLS_DISABLED,
    UNFINISHED_CODE,
)

RLO, ZWJ = "\u202e", "\u200d"


def run(rule_id: str, src: str, path: str = "src/server/m.ts") -> list[Finding]:
    rules: list[Rule] = [r for r in RULES if r.meta.id == rule_id]
    found = analyze([SourceFile(path, src)], rules=rules).findings
    return [f for f in found if f.rule_id == rule_id]


def lines(findings: list[Finding]) -> list[int]:
    return [f.location.start_line for f in findings]


# ---------------------------------------------------------------- SC-CODE-001


def test_tls_option_and_env_forms():
    src = (
        "new https.Agent({ rejectUnauthorized: false });\n"
        "agent.options.rejectUnauthorized = false;\n"
        'spawn("node", ["x.js"], { env: { ...process.env, NODE_TLS_REJECT_UNAUTHORIZED: "0" } });\n'
        "process.env.NODE_TLS_REJECT_UNAUTHORIZED = 0;\n"
        'process.env.NODE_TLS_REJECT_UNAUTHORIZED = "1";\n'
        "const ok = { rejectUnauthorized: isProd };\n"
    )
    assert lines(run(TLS_DISABLED.id, src)) == [1, 2, 3, 4]


def test_package_json_script_and_broken_manifest():
    script = "cross-env NODE_TLS_REJECT_UNAUTHORIZED=0 node s.js"
    manifest = f'{{\n  "scripts": {{\n    "start": "{script}"\n  }}\n}}\n'
    [f] = run(TLS_DISABLED.id, manifest, "package.json")
    assert f.location.start_line == 3 and "`start`" in f.message
    # npm can't run anything from a package.json that isn't JSON.
    assert (
        run(
            TLS_DISABLED.id,
            '{ "scripts": { "start": "NODE_TLS_REJECT_UNAUTHORIZED=0 x" ',
            "package.json",
        )
        == []
    )


# ---------------------------------------------------------------- SC-CODE-002


def test_an_empty_catch_matters_only_around_a_state_changing_call():
    src = (
        "async function a() { try { JSON.parse(x) } catch {} }\n"
        'async function b() { try { await db.from("t").insert(r) } catch (e) {} }\n'
        'async function c() { try { await db.from("api_logs").insert(r) } catch (e) {} }\n'
        "const seen = new Map();\n"
        "function d() { try { seen.delete(k) } catch (e) {} }\n"
    )
    found = run(SWALLOWED_EXCEPTION.id, src)
    assert [(f.location.start_line, f.severity) for f in found] == [(2, Severity.HIGH)]
    assert "db.from.insert" in found[0].message and found[0].evidence == "catch (e)"


def test_console_only_catch_is_flagged_only_around_sensitive_calls():
    src = (
        "async function r() { try { await fetch(u) } catch (e) { console.error(e) } }\n"
        "async function p() { try { await stripe.charges.create(c) } catch { console.log(1) } }\n"
        'function q() { try { await fetch(u, { method: "post" }) } catch { console.warn() } }\n'
    )
    found = run(SWALLOWED_EXCEPTION.id, src)
    assert lines(found) == [2, 3]
    assert all(f.severity is Severity.HIGH and "only logs" in f.message for f in found)


def test_auth_reads_and_hashes_are_not_sensitive():
    src = (
        "async function s() { try { await sb.auth.getSession() } catch { console.error(1) } }\n"
        'function h(p) { try { createHash("md5").update(p) } catch { console.error(1) } }\n'
        "async function o() { try { await sb.auth.signOut() } catch { console.error(1) } }\n"
    )
    assert lines(run(SWALLOWED_EXCEPTION.id, src)) == [3]


def test_promise_catch_only_when_discarded_and_sensitive():
    src = (
        "const body = await req.json().catch(() => null);\n"
        'fetch(u, { method: "DELETE" }).catch(() => {});\n'
        "audio.play().catch(() => {});\n"
        'const f = () => fetch(u, { method: "POST" }).catch(() => null);\n'
        "await axios.post(u, d).catch(() => {}).finally(done);\n"
        'fetch(u, { method: "POST" }).catch((e) => setError(e));\n'
    )
    found = run(SWALLOWED_EXCEPTION.id, src)
    assert lines(found) == [2, 4, 5]
    assert found[0].evidence == ".catch(() => {})"


def test_handled_catches():
    src = (
        "async function a() { try { await db.save(x) } catch (e) { console.error(e); throw e } }\n"
        "async function b() { try { await db.save(x) } catch { return Response.json({}, s500) } }\n"
        "function c(s) { try { new URL(s); return true } catch { return false } }\n"
        "async function d() { try { await db.save(x) } catch { /* cron retries it */ } }\n"
        "function e(s): Date | null { try { return parse(s) } catch { return null } }\n"
    )
    assert run(SWALLOWED_EXCEPTION.id, src) == []


def test_todo_comment_is_not_an_explanation():
    src = "async function a() { try { await db.save(x) } catch (e) {\n  // TODO: handle\n} }\n"
    assert lines(run(SWALLOWED_EXCEPTION.id, src)) == [1]


def test_test_files_and_scripts():
    src = "async function a() { try { await db.save(x) } catch {} }\n"
    assert run(SWALLOWED_EXCEPTION.id, src, "src/orders.test.ts") == []
    logged = "try { await prisma.user.create(d) } catch (e) { console.error(e) }\n"
    assert run(SWALLOWED_EXCEPTION.id, logged, "scripts/seed.mjs") == []
    assert lines(run(SWALLOWED_EXCEPTION.id, logged, "lib/users.mjs")) == [1]


# ---------------------------------------------------------------- SC-CODE-003


def test_unfinished_throws():
    src = (
        'function a() { throw new Error("Method not implemented."); }\n'
        "function b() { throw new NotImplementedError(); }\n"
        'function c() { throw new Error("TODO"); }\n'
        'function d() { throw new Error("Todo not found"); }\n'
        "function e(t) { throw new Error(`Provider ${t} not implemented`); }\n"
        'function f() { throw "not yet implemented"; }\n'
    )
    assert lines(run(UNFINISHED_CODE.id, src)) == [1, 2, 3, 6]


def test_guard_stub_shapes():
    src = (
        "export function verifyWebhook(p: string) { return true; }\n"
        "const checkAccess = async () => true;\n"
        "class Gate { isAuthorized() {} }\n"
        "function assertNever(x: never): void {}\n"
        "function exhaustiveCheck(_x: never) {}\n"
        "const handleCheck = () => {};\n"
        "const opts = { validateStatus: () => true };\n"
        "function verifyToken(t: string) { return jwt.verify(t, key); }\n"
        "function isAllowed() {\n  // every plan includes exports\n  return true;\n}\n"
    )
    found = run(UNFINISHED_CODE.id, src)
    assert lines(found) == [1, 2, 3]
    assert "always returns true" in found[0].message and "empty body" in found[2].message


def test_overridable_methods_are_exempt():
    src = (
        "class BaseVerifier { verify() { return true; } }\n"
        "abstract class Hooks { check() { return true; } }\n"
        "abstract class Jobs { run() { throw new Error('not implemented'); } }\n"
        "class Notifier { send() { throw new Error('not implemented'); } }\n"
        "class Email extends Notifier { send() { return mail(); } }\n"
        "class Sms extends BaseVerifier {}\n"
    )
    assert run(UNFINISHED_CODE.id, src) == []


# ---------------------------------------------------------------- SC-CODE-004


def test_credential_comparison_forms_and_redaction():
    src = (
        'if (req.body.password === "hunter2-hunter2") ok();\n'
        'if ("letmein-now" == pin) ok();\n'
        'if (headers.get("X-Api-Key") !== "k-12345") deny();\n'
        'if (form.password.value === "abc12345") ok();\n'
    )
    found = run(HARDCODED_CREDENTIAL.id, src)
    assert lines(found) == [1, 2, 3, 4]
    assert "hunter2-hunter2" not in found[0].evidence


def test_placeholder_and_config_checks_are_not_credentials():
    src = (
        'if (!apiKey || apiKey === "test-key") useMock();\n'
        'const on = !!key && key !== "your-key-here";\n'
        'if (process.env.ADMIN_PASSWORD === "admin") warn();\n'
        "const secret = process.env.JWT_SECRET;\n"
        'if (secret === "change-me") warn();\n'
        'if (secret === "change-me") throw new Error("set JWT_SECRET");\n'
        'if (!token || token !== "abc-123") deny();\n'
    )
    assert lines(run(HARDCODED_CREDENTIAL.id, src)) == [7]


# ---------------------------------------------------------------- SC-CODE-009


def test_one_finding_per_random_value():
    src = (
        "export function issue() {\n"
        "  const resetToken = Math.random().toString(36).slice(2);\n"
        "  save({ token: resetToken });\n"
        "  return { resetToken };\n"
        "}\n"
    )
    assert lines(run(PREDICTABLE_RANDOM.id, src)) == [2]


def test_random_through_an_opaque_call_is_not_followed():
    src = (
        "async function f() {\n"
        "  const id = Math.random();\n"
        "  const reply = await agent.run(id);\n"
        "  const token = reply.text;\n"
        "  const nonce = btoa(String(id));\n"
        "}\n"
    )
    assert lines(run(PREDICTABLE_RANDOM.id, src)) == [5]


def test_secret_named_helper_is_reported_where_defined():
    src = (
        "const makeOtp = () => String(Math.floor(Math.random() * 1e6));\n"
        "function send() { const otp = makeOtp(); sms(otp); }\n"
    )
    assert lines(run(PREDICTABLE_RANDOM.id, src)) == [1]


# ---------------------------------------------------------------- SC-CODE-010


def test_jsx_text_and_template_literals_count_as_strings():
    src = (
        f"const a = <p>x{RLO}y</p>;\n"
        f"const b = `x ${{v}} {RLO}`;\n"
        f"// {RLO} comment\n"
        f"const c = <p>👨{ZWJ}👩 family</p>;\n"
    )
    found = run(INVISIBLE_UNICODE.id, src, "app/page.tsx")
    assert [(f.location.start_line, f.severity) for f in found] == [
        (1, Severity.MEDIUM),
        (2, Severity.MEDIUM),
        (3, Severity.HIGH),
    ]


def test_emoji_joiner_in_a_comment_is_not_flagged_but_a_stray_one_is():
    for path, comment in (("lib/a.ts", "//"), ("app/a.py", "#")):
        src = f"{comment} 🧑{ZWJ}⚕️ care team\n{comment} ca{ZWJ}re\n"
        assert lines(run(INVISIBLE_UNICODE.id, src, path)) == [2], path


def test_a_plain_js_class_stub_does_not_crash_the_rule():
    # The class lookup named a TypeScript-only node type, and a JS grammar rejects the
    # whole query (found by the second noise study).
    src = "export class AuthService {\n  verifyToken(token) {\n    return true;\n  }\n}\n"
    found = analyze([SourceFile("server/auth.js", src)]).findings
    assert "SC-META-003" not in {f.rule_id for f in found}
    assert [f.rule_id for f in found] == ["SC-CODE-003"]
