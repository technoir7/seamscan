"""SC-CODE-005..008 on TS/JS: details the benchmark cases don't pin down (which shapes count,
where findings point, what messages say)."""

from seamscan.analysis import analyze
from seamscan.model import Finding, SourceFile
from seamscan.rules.base import Rule
from seamscan.rules.injection import CODE_EVAL, JWT_UNVERIFIED, RULES, SHELL_BUILT, SQL_BUILT


def run(rule_id: str, src: str, path: str = "server/app.ts") -> list[Finding]:
    rules: list[Rule] = [r for r in RULES if r.meta.id == rule_id]
    found = analyze([SourceFile(path, src)], rules=rules).findings
    assert not [f for f in found if f.rule_id == "SC-META-003"], found
    return [f for f in found if f.rule_id == rule_id]


def lines(findings: list[Finding]) -> list[int]:
    return [f.location.start_line for f in findings]


# ---------------------------------------------------------------- SC-CODE-005

JWT = 'import jwt from "jsonwebtoken";\n'


def test_renamed_identity_claim_is_trusted():
    src = JWT + (
        "export function f(t: string) {\n  const { sub: userId } = jwt.decode(t) as any;\n}\n"
    )
    assert lines(run(JWT_UNVERIFIED.id, src)) == [3]


def test_reads_through_a_renamed_binding_are_followed():
    src = JWT + (
        "export function f(t: string) {\n"
        "  const { tenant: org } = jwt.decode(t) as any;\n"
        "  if (org !== 'acme') throw new Error('no');\n"
        "}\n"
    )
    assert lines(run(JWT_UNVERIFIED.id, src)) == [3]


def test_expiry_only_reads_and_non_auth_returns_are_not_trust():
    src = JWT + (
        "export function expiresSoon(t: string) {\n"
        "  const c = jwt.decode(t) as any;\n"
        "  return c.exp * 1000 < Date.now() + 60000;\n"
        "}\n"
        "export function tokenForLog(t: string) {\n"
        "  return jwt.decode(t);\n"
        "}\n"
    )
    assert run(JWT_UNVERIFIED.id, src) == []


def test_verifying_a_different_token_does_not_excuse_the_decode():
    src = JWT + (
        "export function f(a: string, b: string, k: string) {\n"
        "  jwt.verify(b, k);\n"
        "  return jwt.decode(a)?.role;\n"
        "}\n"
    )
    assert lines(run(JWT_UNVERIFIED.id, src)) == [4]


def test_verify_allowing_none_is_not_an_exemption_and_is_reported():
    src = JWT + (
        "export function getUser(t: string, k: string) {\n"
        "  jwt.verify(t, k, { algorithms: ['NONE'] });\n"
        "  return jwt.decode(t);\n"
        "}\n"
    )
    assert lines(run(JWT_UNVERIFIED.id, src)) == [3, 4]


def test_client_files_may_decode_for_display():
    src = '"use client";\n' + JWT
    src += "export function f(t: string) {\n  return jwt.decode(t)?.role;\n}\n"
    assert run(JWT_UNVERIFIED.id, src, "components/Nav.tsx") == []


# ---------------------------------------------------------------- SC-CODE-006


def test_sink_in_a_builder_chain_points_at_its_own_line():
    src = (
        "export function f(knex: any, term: string) {\n"
        "  return knex('posts')\n"
        "    .where('a', 1)\n"
        "    .whereRaw(`title LIKE '%${term}%'`);\n"
        "}\n"
    )
    [f] = run(SQL_BUILT.id, src)
    assert f.location.start_line == 4
    assert "`.whereRaw`" in f.message


def test_message_names_the_callee_as_written():
    src = (
        'import { pool } from "@/lib/db";\n'
        "export async function f(id: string) {\n"
        "  const q = `SELECT * FROM t WHERE id = ${id}`;\n"
        "  return pool.query(q);\n"
        "}\n"
    )
    [f] = run(SQL_BUILT.id, src)
    assert "`pool.query` is built from values (via `q`)" in f.message


def test_ambiguous_names_need_sql_text_and_unambiguous_ones_do_not():
    src = (
        "export async function f(db: any, re: RegExp, s: string) {\n"
        "  db.query(`{ user(id: ${s}) { name } }`);\n"
        "  re.exec(`${s}`);\n"
        "  String.raw({ raw: `${s}` });\n"
        "  db.execute(`CALL refresh(${s})`);\n"
        "}\n"
    )
    assert lines(run(SQL_BUILT.id, src)) == [5]


def test_tagged_templates_and_bare_parameters_are_safe():
    src = (
        "export async function f(sql: any, db: any, id: string, text: string) {\n"
        "  await sql`SELECT * FROM t WHERE id = ${id}`;\n"
        "  await db.$queryRaw`SELECT * FROM t WHERE id = ${id}`;\n"
        "  await db.query(text);\n"
        "}\n"
    )
    assert run(SQL_BUILT.id, src) == []


def test_placeholder_list_needs_an_inert_callback():
    safe = "ids.map((_, i) => `$${i + 1}`).join(',')"
    unsafe = "ids.map((id) => `'${id}'`).join(',')"
    template = (
        "export async function f(pool: any, ids: string[]) {{\n"
        "  return pool.query(`SELECT * FROM t WHERE id IN (${{{}}})`, ids);\n"
        "}}\n"
    )
    assert run(SQL_BUILT.id, template.format(safe)) == []
    assert lines(run(SQL_BUILT.id, template.format(unsafe))) == [2]


# ---------------------------------------------------------------- SC-CODE-007


def test_promisified_exec_and_sh_c_are_shell_sinks():
    src = (
        'import { exec, spawn } from "node:child_process";\n'
        'import util from "node:util";\n'
        "const run = util.promisify(exec);\n"
        "export async function f(host: string) {\n"
        "  await run(`ping ${host}`);\n"
        "  spawn('bash', ['-c', `dig ${host}`]);\n"
        "  spawn('dig', [host]);\n"
        "}\n"
    )
    assert lines(run(SHELL_BUILT.id, src)) == [5, 6]


def test_shell_option_with_fixed_text_is_fine_and_any_value_in_argv_is_not():
    src = (
        'import { spawn } from "child_process";\n'
        "export function f(script: string) {\n"
        "  spawn('npm', ['run', 'build'], { shell: true });\n"
        "  spawn('npm', ['run', script], { shell: true });\n"
        "}\n"
    )
    [f] = run(SHELL_BUILT.id, src)
    assert f.location.start_line == 4
    assert "not a literal" in f.message


def test_shell_quote_counts_only_where_applied():
    src = (
        'import { execSync } from "child_process";\n'
        'import { quote } from "shell-quote";\n'
        "export function f(a: string, b: string) {\n"
        "  execSync(`tar -czf ${quote([a])} ${quote([b])}`);\n"
        "  execSync(`tar -czf ${quote([a])} ${b}`);\n"
        "}\n"
    )
    [f] = run(SHELL_BUILT.id, src)
    assert f.location.start_line == 5
    assert "built from values" in f.message


# ---------------------------------------------------------------- SC-CODE-008


def test_eval_family_messages_and_literals():
    src = (
        "import vm from 'node:vm';\n"
        "export function f(code: string, cb: () => void) {\n"
        "  eval('1 + 1');\n"
        "  new Function('a', code);\n"
        "  new vm.Script(code);\n"
        "  setTimeout(cb, 10);\n"
        "  setTimeout(`tick(${code})`, 10);\n"
        "}\n"
    )
    found = run(CODE_EVAL.id, src)
    assert lines(found) == [4, 5, 7]
    assert found[0].message.startswith("`new Function` runs code")


def test_dom_sinks_are_skipped_on_the_server_and_append_counts():
    src = "export function f(el: HTMLElement, s: string) {\n  el.innerHTML += `<li>${s}</li>`;\n}\n"
    assert lines(run(CODE_EVAL.id, src, "public/list.ts")) == [2]
    assert run(CODE_EVAL.id, src, "app/api/x/route.ts") == []


def test_purify_instances_and_constant_json_count_as_safe():
    src = (
        'import createDOMPurify from "dompurify";\n'
        "const DOMPurify = createDOMPurify(window);\n"
        "const LD = { name: 'Acme', tags: ['a', 'b'] };\n"
        "export function A({ html }: { html: string }) {\n"
        "  return (\n"
        "    <div>\n"
        "      <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }} />\n"
        "      <script dangerouslySetInnerHTML={{ __html: JSON.stringify(LD) }} />\n"
        "      <div dangerouslySetInnerHTML={{ __html: html }} />\n"
        "    </div>\n"
        "  );\n"
        "}\n"
    )
    assert lines(run(CODE_EVAL.id, src, "components/A.tsx")) == [9]
