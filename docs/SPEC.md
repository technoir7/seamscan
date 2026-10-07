# seamscan — Technical Specification

**Status:** Draft 1 · **Owner:** Aaron Fung · **Written:** 2026-10-07
**This document is the source of truth.** Code, README and roadmap follow it.
When a decision changes, edit this file first (and add a line to the Changelog
at the bottom). Decisions with real trade-offs get a short record in
`docs/decisions/` (ADR-NNN-title.md). Anything not written here is not agreed.

---

## 1. Summary

seamscan is a deterministic, offline-first static analyzer that catches the
security and correctness failures AI coding tools most often ship. Its focus is
the stacks those tools generate: Python web apps and TypeScript/JavaScript apps,
especially Next.js / Vite frontends on Supabase or Firebase.

It has two modes:

- **`scan`**: checks a change (git diff, staged files, or one agent edit) and
  reports only findings the change introduced. For CI, pre-commit and coding
  agents.
- **`audit`**: checks a whole repository and writes a client-ready report. For
  consulting engagements and one-off reviews.

What makes it worth building, and worth showing:

1. **Cross-file checks for the vibe-coded stack.** It links Supabase migration
   SQL, Firebase rules, env files and client code in one static pass. For
   example: "table `profiles` has no row-level security *and* is queried from
   a browser component with the anon key." That combination caused
   CVE-2025-48757 (170 Lovable apps exposed) and the Moltbook breach (Jan
   2026). The existing tools either need a live database (Supabase's splinter),
   are closed SaaS URL scanners, or don't know these frameworks at all.
2. **A public benchmark with measured precision and recall.** It's a labelled
   corpus of AI-style flaws and hard negatives, with a held-out split, scored
   in CI. No vendor in this space publishes this.
3. **Gating that teams can actually adopt.** A baseline and ratchet mean CI
   fails only on *new* findings. Suppressions need a written reason. Output is
   SARIF for GitHub code scanning.

The principle behind it is the one this whole body of work rests on:
**AI drafts, fixed rules decide, people approve anything consequential,
everything is recorded.** seamscan contains no LLM in its detection path.

---

## 2. Current state (v0.2.1, baseline for comparison)

Recorded so the improvement can be measured and told honestly.

- One 1,370-line file (`seamscan.py`) and 20 unit tests (all pass).
- Detects things by running regexes over raw diff text. Known bugs:
  `re.DOTALL` matches spill across file boundaries, `PUBLIC_KEY_PATH` is
  wrongly flagged as a secret, and one line can raise two findings (see
  `REVIEW.md`).
- Missed 5 of 8 planted flaws in a 2026-10-07 smoke test: a live Stripe key,
  `except: pass`, `NotImplementedError`, a hallucinated import, and a
  hardcoded password check. Plain `.py` files aren't recognized as Python
  without a `pyproject.toml` or `requirements.txt`.
- The terminal says "ALL CHECKS PASSED" while `verdict.md` says "Failures
  Detected". The exit code ignores import failures.
- `pip install .` fails: setuptools finds the 7 committed output folders as
  packages.
- Mixes two jobs: running the target repo's own tests, linters and audits, and
  finding risky patterns. The rewrite keeps only the second (§4.2).

**Recorded "before" score (M1, 2026-10-07).** The v0.2 detectors were run
through the 44-case seed corpus. They're scored on rule alone, with no location
needed, which is lenient (`bench/results/v0.2.2-legacy.json`):

| Split | Precision | Recall |
|---|---|---|
| dev (32 cases) | 0.62 | 0.44 |
| holdout (12 cases) | 0.75 | 0.43 |
| all | 0.65 | 0.44 (11 of 25) |

The new engine has to beat this, with exact locations, before it replaces the
legacy CLI (end of M2).

---

## 3. Users and use cases

| User | Use | Mode | What they need |
|---|---|---|---|
| Founder or solo dev shipping an AI-built app | "Is this safe to launch?" | `audit` | A readable report with clear fixes, no setup |
| Small team using AI coding tools | Block new risky code in PRs | `scan` in CI | Low noise, baselines, SARIF |
| Developer running a coding agent | Agent fixes its own mistakes before finishing | `scan` via Claude Code hook | Fast (≤1 s on edited files), compact output |
| Aaron as a consultant | Offer A ("prototype to production") audit | `audit --format md` | A professional report, honest methodology section |
| Hiring manager or client evaluating Aaron | Judge the engineering | README, benchmark, code | Real numbers, clean architecture, honest limits |

---

## 4. Scope

### 4.1 In scope (v1.0)

- Languages: Python 3.8+ source (analyzer runs on 3.11+), TypeScript, TSX,
  JavaScript, JSX.
- Config and data files: Supabase migrations (`supabase/migrations/*.sql`),
  Firebase rules (`firestore.rules`, `storage.rules`, `database.rules.json`),
  `.env*` files, `package.json`, `requirements*.txt`, `pyproject.toml`.
- Framework awareness: Next.js (app and pages router), Vite/React, Express,
  FastAPI, Flask, Django settings, Supabase JS client, Firebase JS SDK.
- About 25 rules (§7), the benchmark (§8), baseline/ratchet/suppressions
  (§9), reporters (§10), integrations (§11).

### 4.2 Non-goals (v1.0)

- **No LLM in detection.** LLMs may *generate* benchmark cases (recorded and
  frozen, §8.3), never judge findings.
- **No auto-fix.** seamscan reports; the human or agent fixes.
- **No running the target's tests, linters or type checkers.** That's CI's
  job. (v0.2.1 did this; it's removed.)
- **No dependency CVE scanning.** OSV, Dependabot and `pip-audit` do this
  well. seamscan only checks that packages *exist* and aren't suspiciously new
  (§7.7).
- **No git-history secret scanning.** gitleaks and trufflehog own this.
- **No full interprocedural data-flow analysis.** Taint-style rules are
  intra-procedural and labelled with their confidence.
- **No live database or URL probing.** It's static only. It complements
  splinter and black-box scanners rather than replacing them.
- No other languages, no hosted service, no PR-comment bot.

---

## 5. Architecture

### 5.1 Principles (from Aaron's standing rules)

- **Layers with real barriers.** Each layer uses only the public interface of
  the one below. Rules never touch the filesystem, git or the network.
- **Pure core, I/O at the edges.** Parsing, facts, rules, policy and
  rendering are pure functions over in-memory data. Only `workspace/`,
  `supply/` and `cli.py` do I/O. Rules are testable with no mocks.
- **Fail loudly.** A file that can't be parsed produces a visible
  `SC-META-002` finding. Nothing is skipped silently.
- **Deterministic.** The same inputs and the same offline data give
  byte-identical JSON. Findings are sorted, with no timestamps unless asked
  for.
- **No speculative generality.** No plugin system, no rule DSL. Rules are
  Python functions. Add extension points when a third case proves the need.

### 5.2 Package layout

`src/` layout. This also fixes the packaging bug.

```
src/seamscan/
  __init__.py            # __version__ only
  model.py               # Finding, Location, Severity, Confidence, RuleMeta, fingerprint()
  workspace/             # I/O EDGE: what to analyze
    git.py               #   ChangeSet from `git diff` (added/modified line ranges, renames)
    files.py             #   file enumeration: git ls-files, .seamscanignore, size/binary/vendor skips
  parse/                 # pure: bytes -> syntax trees
    python.py            #   stdlib `ast` (+ comments via `tokenize` for suppressions)
    javascript.py        #   tree-sitter TS/TSX/JS/JSX
    sql.py               #   Supabase migration statement scanner (ADR-001: no sqlglot)
    firebase_rules.py    #   tokenizer for `allow <ops>: if <expr>;` + JSON RTDB rules
    envfile.py           #   .env parsing (values kept in memory, never printed)
    manifests.py         #   package.json, requirements, pyproject dependencies
  facts/                 # pure: trees -> project-level facts
    project.py           #   ProjectModel: frameworks, file roles (client/server/test), env usage
    supabase.py          #   replayed schema state: tables, RLS on/off, policies, definer functions
    secrets.py           #   secret classification: provider prefixes, JWT role claim, entropy
  rules/                 # pure: (ProjectModel, file trees) -> Finding[]
    base.py              #   Rule protocol + RuleContext
    registry.py          #   explicit list of rules (no discovery magic)
    secrets.py  supabase.py  firebase.py  web.py  code.py  deps.py  tests_integrity.py  meta.py
  policy/                # pure: Finding[] -> verdict
    config.py            #   seamscan.toml (stdlib tomllib)
    suppress.py          #   inline ignores with mandatory reasons
    baseline.py          #   baseline file, ratchet comparison
    verdict.py           #   blocking vs non-blocking, exit code
  supply/                # I/O EDGE: package registries
    registry.py          #   PyPI/npm lookups (stdlib urllib), cache, offline snapshot
  report/                # pure: verdict -> text
    terminal.py  json.py  sarif.py  markdown.py  agent.py
  integrations/
    claude_hook.py       #   stdin hook JSON -> scan -> hook response JSON
  analysis.py            # pure: SourceFile[] (+ ChangeSet) -> Finding[]; the whole pipeline, no I/O
  cli.py                 # composition root: the only place that wires I/O to the core
bench/                   # benchmark corpus, runner, scorer (§8)
docs/
  SPEC.md                # this file
  decisions/             # ADRs
  rules/SC-XXX-NNN.md    # one page per rule (required, §12.2)
schemas/
  findings.v1.schema.json
tests/
action.yml               # GitHub composite action
.pre-commit-hooks.yaml
```

### 5.3 Layer contract (enforced in CI)

```
cli ─▶ integrations ─▶ report, policy ─▶ rules ─▶ facts ─▶ parse ─▶ model
 │                                         ▲
 └──▶ workspace, supply (I/O edges) ───────┘ (pass plain data in; never imported by rules)
```

An architecture test (`tests/test_architecture.py`) reads every module's
imports with `ast` and fails on a violation. It makes this a test, not a hope.
It's a small in-house test rather than `import-linter`, because it must also
forbid stdlib modules (`subprocess`, `urllib`, `socket`), and it adds no
dependency:

- `rules`, `facts`, `parse`, `policy` and `report` must not import
  `workspace`, `supply`, `subprocess`, `urllib`, `socket` or `os.environ`.
- `parse` must not import `facts` or `rules`. `facts` must not import `rules`.
- Nothing imports `cli`.

### 5.4 Core data model (`model.py`)

```python
class Severity(IntEnum):        # impact if real
    LOW = 1; MEDIUM = 2; HIGH = 3; CRITICAL = 4

class Confidence(IntEnum):      # how likely the finding is real
    LOW = 1; MEDIUM = 2; HIGH = 3

@dataclass(frozen=True, order=True)
class Location:
    path: str                   # repo-relative, POSIX separators
    start_line: int             # 1-based
    start_col: int              # 1-based
    end_line: int
    end_col: int

@dataclass(frozen=True)
class RuleMeta:
    id: str                     # "SC-SUPA-001"; never reused once released
    title: str
    severity: Severity          # default; a rule may raise it per finding with a stated reason
    confidence: Confidence
    cwe: tuple[str, ...]        # ("CWE-284",)
    languages: frozenset[str]
    summary: str                # one line, used in agent output
    help_uri: str               # docs/rules/<id>.md on GitHub

@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Severity
    confidence: Confidence
    location: Location
    message: str                # specific: names the table/var/function
    evidence: str               # snippet, secrets redacted (§6.4)
    related: tuple[Location, ...] = ()   # e.g. the client file that queries the table
    fingerprint: str = ""       # set by fingerprint(), see below
```

Severity (impact) and confidence (likelihood) are separate on purpose.
v0.2.1 mixed "which tool failed" with "how bad", and the rewrite drops that.

**Fingerprint.** `sha256(rule_id ‖ path ‖ normalized_snippet ‖ k)`, where
`normalized_snippet` is the matched node's source with whitespace collapsed
and secrets redacted, and `k` is the occurrence index among identical
`(rule, path, snippet)` triples. It survives line shifts and reformatting,
and changes when the offending code changes. It's used by the baseline and
emitted as SARIF `partialFingerprints["seamscan/v1"]`.

### 5.5 Scan pipeline

```
workspace.files / workspace.git  ─▶  FileSet (+ ChangeSet in scan mode)
parse.*                          ─▶  ParsedFile per file (or ParseError -> SC-META-002)
facts.project / facts.supabase   ─▶  ProjectModel (whole-repo facts, needed even in scan mode)
rules.registry                   ─▶  Finding[] (all findings, all files in scope)
scope filter (scan mode only)    ─▶  keep findings whose location or any related
                                     location overlaps an added/modified line range
policy.suppress / baseline       ─▶  Finding[] tagged suppressed/baselined/new
policy.verdict                   ─▶  Verdict(blocking, non_blocking, exit_code)
report.*                         ─▶  output
```

Scan mode still parses whatever the cross-file facts need: all migrations,
rules files, env files and manifests, plus changed source files. It does not
parse every source file. Unchanged client files are matched to tables by a
cheap lexical index (`.from('<name>')`) built during enumeration. ADR-002
records the trade-off: a finding is in scope if *either* side of a cross-file
relationship changed.

**Diff source.** `git diff --unified=0 --no-color --no-ext-diff -M <base>`.
Hunks are parsed into per-file added line ranges, following renames. The base
defaults to `merge-base(HEAD, origin/HEAD)` in CI, `HEAD` for working-tree
scans, and the index for `--staged`. Working directly on files and line
ranges, never regexes over diff text, removes v0.2.1's
cross-file-bleed class of bugs entirely.

### 5.6 File roles (`facts/project.py`)

Several rules depend on whether code runs in the **browser** or on the
**server**. The classification order is: first match wins, and each match
records its reason (shown in `--explain`).

1. `seamscan.toml [paths] client/server` globs (explicit override).
2. Directive: a file starting with `"use client"` → client;
   `"use server"` → server.
3. Next.js conventions: `app/**/route.{ts,js}`, `middleware.*`, `pages/api/**`,
   `*.server.*`, `app/**/actions.*` with `"use server"` → server. Other
   files under `app/` → server component (code runs on the server, but
   `NEXT_PUBLIC_*` values are inlined into client bundles).
4. Supabase Edge Functions (`supabase/functions/**`) → server (Deno).
5. Vite/CRA: `src/**` → client unless under `server/`, `api/`, `functions/`.
6. Python files → server.
7. Test files (`test_*.py`, `*_test.py`, `*.test.*`, `*.spec.*`, `tests/**`,
   `__tests__/**`) → test (most rules skip these; the SC-TEST rules target
   them).
8. Otherwise → unknown. Rules that need a role skip unknown files and
   count them in `--stats`.

### 5.7 Supabase schema replay (`facts/supabase.py`)

Migrations are applied in filename order (`<timestamp>_name.sql`) as a pure
fold over statements:

| Statement | Effect on state |
|---|---|
| `CREATE TABLE [IF NOT EXISTS] [schema.]name` | add table (schema defaults to `public`), `rls=False` |
| `ALTER TABLE name ENABLE / DISABLE ROW LEVEL SECURITY` | set `rls` |
| `ALTER TABLE name FORCE ROW LEVEL SECURITY` | note `forced` |
| `CREATE POLICY name ON table [AS ...] FOR op TO roles USING (e) [WITH CHECK (e)]` | add policy |
| `DROP TABLE / DROP POLICY` | remove |
| `CREATE [OR REPLACE] FUNCTION ... SECURITY DEFINER` (without `SET search_path`) | add definer function |
| `CREATE VIEW` (without `security_invoker`) | add view |
| `GRANT ... TO anon / authenticated` | record grants |
| anything else | ignored, counted in `--stats` |

**ADR-001 (decided 2026-10-07):** a small in-house statement scanner, no
`sqlglot`. The spike showed sqlglot returns raw unparsed text for exactly the
statements these rules need: RLS toggles, `CREATE/DROP POLICY`, and
`SECURITY DEFINER ... SET search_path`. The scanner splits on `;` outside
quotes, dollar-quoting and comments, then matches each statement's head against
the forms above.

---

## 6. Detection engine details

### 6.1 Python

- Parse with stdlib `ast` (feature version 3.8–3.13).
- Comments come from `tokenize`, for suppressions only.
- Use a small set of helpers over the tree: `calls_to(module, name)`,
  `kwarg_value(call, name)`, `is_literal(node)`, `string_parts(node)` (the
  f-string, `%` and `.format` components), and `function_containing(node)`.
- Import aliases are resolved per module (`import requests as r`), so rules
  match `r.get(..., verify=False)`.

### 6.2 TypeScript and JavaScript

- `tree-sitter==0.26.*`, `tree-sitter-typescript==0.23.*`,
  `tree-sitter-javascript==0.25.*`, all pinned exactly.
  - These are the only parser dependencies. Python has no TS parser in the
    standard library.
  - `tree-sitter-language-pack` is **not** used: its 1.x downloads grammars
    at runtime, which breaks offline and reproducible runs.
- One query file per rule (`rules/queries/*.scm`), compiled once and
  cached.
- The py-tree-sitter API changed in 0.25 and 0.26, so all tree-sitter calls
  go through `parse/javascript.py`. Upgrading means changing one file.
- Import and alias resolution covers ES modules and CommonJS `require` within
  a file.

### 6.3 Intra-procedural "taint-lite"

Used by the injection, SSRF and auth rules. Within one function body:

- **Sources:** request-derived values. Examples: `req.body/query/params`,
  `request.json()`, `searchParams.get`, FastAPI/Flask request objects, Next.js
  `params`, and function parameters of route handlers.
- **Propagation:** assignments, destructuring, string concatenation,
  template literals, f-strings, `.format`, `%`.
- **Sinks:** defined per rule.
- **Sanitizers:** defined per rule, and configurable (e.g. a URL allowlist
  check, `DOMPurify.sanitize`, parameterized query APIs).
- No interprocedural flow. If a value passes through a helper function, the
  rule stays silent. That's a known false-negative source, and it's
  documented on each rule page and measured by the benchmark.

### 6.4 Secret handling (safety of seamscan's own output)

- Secret values are **never** printed whole in any output format. They are
  redacted to `sk_live_51Hx…cE6gJ`: the provider prefix plus the first 4 and
  last 5 characters.
- `.env` values are read into memory for classification only.
- Fingerprints hash the redacted form.
- A test runs every reporter over a corpus containing real-format fake
  secrets and asserts that no full secret appears in the output.

---

## 7. Rule set v1

The format for each rule is: **ID, title**, then severity / confidence /
CWE, then detection logic, a true positive (TP) and a hard negative (HN).
Every rule ships with a docs page and benchmark cases (§12.2). IDs are stable
forever.

### 7.1 Secrets and key exposure

**SC-SEC-001 — Provider secret in source.**
CRITICAL / HIGH / CWE-798.
- Matches known secret prefixes in string literals of non-test files:
  - Stripe `sk_live_` / `rk_live_`
  - AWS `AKIA[0-9A-Z]{16}` (with a 40-char secret nearby)
  - GitHub `ghp_` / `github_pat_`
  - OpenAI `sk-proj-` / `sk-`
  - Anthropic `sk-ant-`
  - Supabase `sb_secret_`
  - Slack `xox[bp]-`
- JWTs are decoded **without verification**, payload only. A Supabase JWT
  whose `role` claim is `service_role` counts as secret.
- Publishable keys are explicitly *not* secret: `pk_live_`,
  `sb_publishable_`, anon JWTs, Firebase web `apiKey` in config objects.
- TP: `const stripe = new Stripe("sk_live_51H…")`
- HN: `const stripe = loadStripe("pk_live_51H…")`; `"sk_test_…"` → LOW instead.

**SC-SEC-002 — Secret reachable from the browser.**
CRITICAL / HIGH / CWE-200, CWE-522. Fires on either:
- (a) a SC-SEC-001-class secret literal in a client file; or
- (b) an env var with a public prefix (`NEXT_PUBLIC_`, `VITE_`,
  `EXPO_PUBLIC_`, `REACT_APP_`) whose `.env*` value classifies as secret, or
  whose *name* contains `SERVICE_ROLE`, `SECRET`, `PRIVATE` or `ADMIN`.

Known-public names like `*_ANON_KEY`, `*_PUBLISHABLE_KEY` and `FIREBASE_*`
config are allowed. The finding links the definition (`.env`) and the use
(client file) as related locations.
- TP: `NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY=eyJ…(role=service_role)`
- HN: `NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ…(role=anon)`

**SC-SEC-003 — Hardcoded fallback for a secret.**
HIGH / HIGH / CWE-1188.
- Matches `os.environ.get("X", "<lit>")`, `os.getenv("X", "<lit>")`,
  `process.env.X || "<lit>"`, `process.env.X ?? "<lit>"`, where `X`
  tokenizes (split on `_`) to include `SECRET`, `KEY`, `TOKEN`, `PASSWORD`,
  `PASS`, `PWD`, `JWT` or `SALT`.
- Excluded: `X` ending in `_PATH`, `_FILE`, `_URL`, `_ID`, `_NAME`, `_DIR`
  (fixes the v0.2.1 `PUBLIC_KEY_PATH` false positive), and empty-string
  defaults.
- TP: `SECRET = os.environ.get("SESSION_SECRET", "dev-secret")`
- HN: `os.environ.get("PUBLIC_KEY_PATH", "/etc/pub.pem")`

**SC-SEC-004 — Env file committed.**
HIGH / HIGH / CWE-538.
- Fires on a tracked `.env`, `.env.local`, `.env.production` or
  `.env.*.local` containing at least one non-placeholder value.
- `.env.example` / `.env.sample` are allowed unless a value classifies as
  secret, in which case it's CRITICAL via SC-SEC-001.

### 7.2 Supabase

**SC-SUPA-001 — Public table without row-level security.**
HIGH → CRITICAL / HIGH / CWE-284.
- Fires when, after replay, a table in `public` has `rls=False`.
- Raised to CRITICAL when any client file calls `.from('<table>')` on a
  Supabase client. That pairing is the CVE-2025-48757 pattern.
- The related locations are the client call sites.
- TP: migration `create table public.messages (...)` with no RLS statement,
  plus `supabase.from('messages').select()` in a `"use client"` file.
- HN: same table with `alter table public.messages enable row level security`
  in a later migration.

**SC-SUPA-002 — Policy allows everyone.**
HIGH / HIGH / CWE-284.
- Fires on a policy with `USING (true)` or `WITH CHECK (true)` for
  `INSERT/UPDATE/DELETE/ALL`, applying to `anon` or `public`, or to
  `authenticated` without a row condition.
- A `SELECT ... USING (true)` policy is LOW and informational, because public
  read tables are a legitimate design.
- HN: `using (auth.uid() = user_id)`.

**SC-SUPA-003 — Unsafe definer objects.**
MEDIUM / HIGH / CWE-269.
- Fires on a `SECURITY DEFINER` function in `public` without
  `SET search_path`, or a view in `public` without `security_invoker = true`
  that selects from an RLS-protected table.
- These are the static equivalents of splinter checks 0010 and 0011.

**SC-SUPA-004 — RLS explicitly disabled.**
HIGH / HIGH / CWE-284. Fires on `DISABLE ROW LEVEL SECURITY` in a migration.
In scan mode, it fires when the change adds that statement.

### 7.3 Firebase

**SC-FIRE-001 — Open security rules.**
CRITICAL / HIGH / CWE-284. Fires on:
- Firestore or Storage `allow read, write: if true;`, or `allow ...: if
  request.time < timestamp.date(...)`, which is Firebase's "test mode"
  default that silently expires.
- RTDB `".read": true` or `".write": true` at the root or a top-level path.
- HN: `allow read: if request.auth != null && request.auth.uid == userId;`

### 7.4 Web and server routes

**SC-WEB-001 — Server write without an auth check.**
HIGH / MEDIUM / CWE-862. Applies to:
- a Next.js route handler exporting `POST/PUT/PATCH/DELETE`
- a `"use server"` action
- an Express handler on a mutating method
- a FastAPI/Flask view on a mutating method

It fires when the function body performs a data write before any call to a
recognized auth primitive. Writes are `supabase.from(..).insert/update/upsert/delete`,
`prisma.*.create/update/upsert/delete*`, `db.insert/update/delete`, or an ORM
`.save()`. Auth primitives are `auth()`, `getServerSession`,
`supabase.auth.getUser`, `currentUser`, `getToken`, `Depends(<name matching
*user*|*auth*>)`, `@login_required`, plus project helpers listed in
`seamscan.toml [auth] primitives`. Middleware-based auth makes this noisy, so
`[auth] protected_paths` globs mark routes as covered by middleware. MEDIUM
confidence is deliberate, and the benchmark measures it.

**SC-WEB-002 — Server-side request to a user-controlled URL (SSRF).**
HIGH / MEDIUM / CWE-918.
- Taint-lite (§6.3) from request input into `fetch`, `axios.*`, `got`,
  `requests.*`, `httpx.*` or `urllib.request.urlopen` as the URL.
- A sanitizer is a call matching `[ssrf] allowlist_checks`, or a comparison of
  `new URL(x).hostname` / `urlparse(x).hostname` against a literal collection.
- TP: `const r = await fetch(searchParams.get("url"))` in a route handler.

**SC-WEB-003 — Permissive debug or CORS config.**
MEDIUM / HIGH / CWE-942, CWE-489. Fires on:
- Flask `app.run(debug=True)` outside `if __name__ == "__main__"` guards
  that check an env var
- Django `DEBUG = True` in `settings.py` / `settings/prod*.py`
- FastAPI `CORSMiddleware(allow_origins=["*"], allow_credentials=True)`
- Express `cors({ origin: true|"*", credentials: true })`

### 7.5 Code patterns (Python and TS/JS)

**SC-CODE-001 — TLS verification disabled.**
HIGH / HIGH / CWE-295. Port of v0.2.1 CLASS-12 to syntax trees. Fires on:
- `requests.*(verify=False)`, `httpx.*(verify=False)`
- `ssl._create_unverified_context`, `ssl.CERT_NONE`
- `rejectUnauthorized: false`
- `NODE_TLS_REJECT_UNAUTHORIZED = "0"` / `process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'`

One finding per call site. Fixes the v0.2.1 double-report.

**SC-CODE-002 — Swallowed exception.**
MEDIUM / HIGH / CWE-390. Fires on:
- Python `except:`, `except Exception:` or `except BaseException:` whose body
  is only `pass`, `...`, `continue` or `return None` (no logging, no re-raise)
- TS/JS `catch` with an empty block, or only `console.log`

Raised to HIGH when the `try` block calls a write sink (§7.4 list) or a
payment/auth API (`stripe.*`, `*.auth.*`).

**SC-CODE-003 — Unfinished code in a shipped path.**
HIGH / HIGH / CWE-1164. In non-test, non-abstract code, fires on:
- `raise NotImplementedError` or `throw new Error(/not implemented|todo/i)`
- a function whose name matches
  `/(auth|verify|validate|check|permission|allowed|charge|refund)/i` and
  whose body is only `pass`, or `return True`, or `return true`

Excluded: `@abstractmethod`, `Protocol` classes, and `.pyi` stubs.
- TP: `def verify_signature(payload, sig): return True`

**SC-CODE-004 — Hardcoded credential comparison.**
HIGH / HIGH / CWE-798. Fires on a comparison (`==`, `===`, `in`) between an
identifier named like password, passwd, pwd, token, secret, api_key or pin, and
a non-empty string literal.
- TP: `if password == "admin":`
- HN: `if password == "":` (an emptiness check)

**SC-CODE-005 — JWT accepted without verification.**
CRITICAL / HIGH / CWE-347. Fires on:
- PyJWT `jwt.decode(..., options={"verify_signature": False})`, or
  `algorithms` including `"none"`
- `jsonwebtoken`'s `jwt.decode(token)` whose result is used in a conditional
  in a server file with no `jwt.verify` call in the same function

**SC-CODE-006 — SQL built from strings.**
HIGH / MEDIUM / CWE-89.
- Taint-lite into `cursor.execute`, `conn.execute`, `db.query`, `sql.raw`,
  `$queryRawUnsafe` or `knex.raw`, where the query argument is an f-string,
  concatenation, `%` or `.format` containing a non-literal.
- Safe forms: parameter tuples and tagged templates (`sql\`...\``,
  `Prisma.sql`).

**SC-CODE-007 — Shell command built from strings.**
HIGH / MEDIUM / CWE-78. Fires on `subprocess.*(..., shell=True)`,
`os.system` or `child_process.exec/execSync`, where the command contains a
non-literal part.

**SC-CODE-008 — Code or HTML evaluated from non-literals.**
HIGH / MEDIUM / CWE-95, CWE-79. Fires on `eval`, `exec`, `new Function` or
`vm.runInThisContext` with a non-literal argument, and on
`dangerouslySetInnerHTML={{__html: x}}` where `x` isn't wrapped in a
configured sanitizer.

**SC-CODE-009 — Predictable randomness for secrets.**
MEDIUM / HIGH / CWE-338. Fires when `Math.random()` or the `random.*` module
supplies a value assigned to, or returned from, a name matching
token, secret, password, otp, nonce, salt, code or session.

**SC-CODE-010 — Invisible or bidirectional Unicode in source.**
HIGH / HIGH / CWE-1007. Fires on bidi control characters or zero-width
characters outside string literals (Trojan Source, CVE-2021-42574). This is a
port of v0.2.1 CLASS-5.

### 7.6 Test integrity (AI agents "make tests pass")

**SC-TEST-001 — Test with no assertion.**
MEDIUM / HIGH. Fires on a pytest test function, or a jest/vitest `it`/`test`
callback, with no `assert`, `pytest.raises`, `expect`, `assert.*`,
`mock.assert_*` or configured helper.

**SC-TEST-002 — Assertion that can't fail.**
MEDIUM / HIGH. Fires on `assert True`, `assert x == x`,
`expect(true).toBe(true)`, or `expect(x).toEqual(x)` with the identical
expression on both sides.

**SC-TEST-003 — Test disabled in this change.**
MEDIUM / HIGH. Scan mode only. Fires on added `@pytest.mark.skip`, `xfail`,
`it.skip`, `describe.skip`, `test.todo`, or `.only` (which disables the rest
of the suite).

### 7.7 Dependencies (the only rules that use the network)

**SC-DEP-001 — Dependency that doesn't exist.**
HIGH / HIGH / CWE-1357. Fires on a package declared in a manifest that gets a
404 from the registry:
- PyPI: `GET https://pypi.org/pypi/<name>/json`
- npm: `GET https://registry.npmjs.org/<name>` (scoped names URL-encoded)

For npm, bare imports in source are also checked, because the import name is
the package name. For Python, only *declared* dependencies are checked,
because import names differ from distribution names (`yaml` vs `PyYAML`).

**SC-DEP-002 — Dependency too new or obscure to trust.**
MEDIUM / MEDIUM. Fires when:
- the package was first published fewer than `min_age_days` (default 30) ago.
  - npm: `time.created`.
  - PyPI: the earliest file `upload-time` from the Simple API JSON (PEP 691,
    `Accept: application/vnd.pypi.simple.v1+json`).
- or, npm only, it has fewer than `min_weekly_downloads` (default 100) via
  `api.npmjs.org/downloads/point/last-week`.

This is the slopsquatting case: hallucinated names that someone has since
registered (e.g. `react-codeshift`, Jan 2026).

**SC-DEP-003 — New dependency runs code at install.**
MEDIUM / HIGH / CWE-829. Fires when a dependency added in this change has
`preinstall`, `install` or `postinstall` scripts in its registry metadata for
the resolved version.

**Network behavior:**
- Responses are cached in `~/.cache/seamscan/registry/` (TTL 7 days for
  existence, 1 day for age and downloads).
- `--offline` uses only the cache plus a bundled snapshot of the top 10k
  PyPI and npm names.
  - A name not in either is reported as "unverified" (LOW), never as missing.
- Network errors are reported, never treated as "exists".
- Requests are sequential with a 10 s timeout, and HTTP 429 responses back
  off and are reported.

### 7.8 Meta

- **SC-META-001 — Suppression without a reason.** LOW. The suppression is
  ignored.
- **SC-META-002 — File could not be parsed.** LOW, or blocking with
  `--strict`.
- **SC-META-003 — Rule crashed on a file.** The rule's other files still run,
  the crash is reported with a traceback in `--debug`, and the exit code
  becomes 3.

### 7.9 Deliberately deferred to v2

These are listed so they aren't half-built now:
- LLM output flowing into exec, SQL or shell
- user input concatenated into a system prompt
- interprocedural taint
- Prisma/Drizzle RLS equivalents
- auth checks on Supabase Edge Functions
- cookie flags (`HttpOnly`, `Secure`, `SameSite`)
- `npm` lockfile integrity

---

## 8. Benchmark ("seambench")

This is the part that turns "a scanner" into evidence.

### 8.1 Case format

```
bench/cases/<case-id>/
  case.toml
  repo/            # minimal file tree (the "after" state)
  base/            # optional "before" tree for scan-mode cases
```

```toml
id = "supa-rls-missing-client-query-01"
description = "messages table created without RLS, read from a client component"
mode = "audit"                # or "scan"
languages = ["sql", "tsx"]
framework = "nextjs-supabase"
split = "dev"                 # "dev" or "holdout"

[provenance]
source = "original"           # original | llm-generated | adapted
model = ""                    # e.g. "claude-sonnet-5" when llm-generated
prompt = ""                   # path under bench/prompts/
upstream = ""                 # e.g. "CWEval task py/cwe-89-01 (Apache-2.0)"

[[expected]]                  # must be found
rule = "SC-SUPA-001"
path = "supabase/migrations/20260101000000_init.sql"
line = 3
tolerance = 2                 # line match window

[[forbidden]]                 # hard negatives: these rules must NOT fire here
rule = "SC-SEC-002"
```

**Fake secrets.** Case files never contain secret-shaped strings literally.
They use placeholders such as `{{FAKE_STRIPE_LIVE}}`, which the runner
replaces when it loads the case. The values come from `bench/fake_secrets.py`,
which builds them by concatenation. That keeps GitHub push protection and
secret scanning quiet without weakening the cases.

**Split integrity.** A test checks that every case's `split` equals the
hash-derived value (`sha256(id)`, the first 8 hex digits mod 10 < 3 →
`holdout`). Cases can't be moved between splits by hand.

### 8.2 Scoring

- A finding matches an expectation when the rule, path, and line (within
  tolerance) all agree. Each expectation matches at most one finding.
- Per rule and in total, it reports true positives, false positives (unmatched
  findings plus any `forbidden` hit), false negatives, precision, recall and
  F1.
- Results are reported **separately for `dev` and `holdout`**, and are never
  blended into one headline number.
- Wall time per case is recorded for the performance budget.

### 8.3 Corpus construction

Targets for v1.0:

| Dimension | Target |
|---|---|
| Cases per rule | ≥ 5 positive + ≥ 5 hard negatives |
| Total cases | ~300 |
| TS/JS share | ≥ 40% |
| Original Supabase/Firebase/Next.js cases | ≥ 60 (none of the public benchmarks cover them) |
| Holdout share | 30%, chosen by hash of the case id |

**Sources:**
1. **Original, hand-written cases.** Each is modeled on a documented real
   incident pattern, such as CVE-2025-48757, Moltbook, or Firebase test-mode
   rules.
2. **LLM-generated cases.**
   - Realistic task prompts, e.g. "add a messages feature to this
     Next.js + Supabase app", are run against named models. The model id, date,
     temperature and prompt are all recorded, and the output is frozen in the
     repo. **Nothing is ever silently regenerated.**
   - Labels are added by hand, and a second pass happens on a different day.
   - This gives the "how often do AI tools produce this" angle.
3. **Adapted public benchmarks.**
   - Source sets: CWEval (Apache-2.0, keep NOTICE), SecCodePLT (MIT),
     BaxBench (MIT repo, but confirm the dataset license first), and
     CyberSecEval (MIT).
   - Attribution goes in `bench/THIRD_PARTY.md`.
   - **Semgrep registry rules and their test files are not used.** The
     Semgrep Rules License forbids reuse in a competing tool.

**Independent holdout (added 2026-10-07):** cases written alongside a rule by
the same author can't be truly held out. The author has seen them, even if
the rule is tuned on `dev` only. So in M7 a second set, `holdout-independent`, is
written by a different author (a separate agent session or model with no access
to `src/seamscan/rules/`). It works from the rule pages in `docs/rules/` alone.
Published headline numbers come from that set.

**Holdout discipline:**
- Rules are developed against `dev` only.
- `holdout` is scored only at milestone ends and before releases.
- A holdout case that leaks into rule development is moved to `dev`, and a
  replacement is written.

### 8.4 Noise in the wild

A labelled corpus overstates precision, so v1.0 also runs `audit` on pinned
commits of **20 public repositories**:
- 10 Next.js/Vite + Supabase/Firebase starters and apps
- 10 FastAPI/Flask/Django apps

It reports **findings per 1,000 lines** and a hand-triaged precision estimate
on a random sample of up to 100 findings. The sample size and method are
stated with the result.

### 8.5 Comparators

- **Comparator tools:** the same corpus is run through Bandit, gitleaks and
  eslint-plugin-security, all permissively licensed.
- **Category mapping:** their rule ids map to seamscan categories in
  `bench/compare/mapping.toml`.
- **What's reported:** coverage per *category* (Supabase, secrets, code
  patterns…). It is presented as "different tools, different goals", never as
  "we beat X".
- **Semgrep and Opengrep:** comparison is an open question (§15).
- **Reference point:** CyberSecEval's Insecure Code Detector reports 96%
  precision and 79% recall.

### 8.6 Budgets in CI

`bench/budget.toml` holds per-rule minimums on `dev`:

| Rule confidence | Precision ≥ | Recall ≥ |
|---|---|---|
| HIGH | 0.95 | 0.85 |
| MEDIUM | 0.80 | 0.70 |

- **Budget enforcement:**
  - The bench job fails if any rule drops below its budget.
  - It also fails if any rule regresses more than 0.02 from the committed
    `bench/results/latest.json`.
  - Budgets only ratchet upward.
- **README results table:**
  - The table is generated (`make bench-readme`).
  - CI fails if the README table is out of date, the same pattern as
    Tribecca's stale-codegen check.

---

## 9. Policy: gating that teams adopt

### 9.1 Blocking rule

- **What blocks:** by default, a finding blocks when severity ≥ HIGH
  **and** confidence ≥ MEDIUM **and** it is not suppressed **and** not in the
  baseline.
- **Everything else** is reported but doesn't fail the run.
- **Configuration:** `[policy] fail_on_severity`, `fail_on_confidence`.

### 9.2 Suppressions

```python
data = requests.get(url, verify=False)  # seamscan: ignore[SC-CODE-001] reason: internal CA, pinned in INFRA-12
```

```ts
// seamscan: ignore-next-line[SC-WEB-001] reason: auth enforced by middleware.ts matcher
```

- **A reason is mandatory.** Without one, the suppression doesn't apply, and
  SC-META-001 is raised.
- **Reporting:** all suppressions are listed in `--stats` and in the audit
  report.

### 9.3 Baseline and ratchet

- `seamscan baseline create` writes `.seamscan/baseline.json`. Entries are
  sorted, and each records `{fingerprint, rule_id, path}`. There are no
  timestamps, so diffs stay clean.
- `scan` and `audit` treat findings in the baseline as existing debt that
  doesn't block.
- `seamscan baseline prune` removes entries that no longer match anything.
- **The ratchet:**
  - `seamscan baseline check --against <base-ref>` fails if the baseline gained
    any entries compared with the base branch.
  - Debt can only shrink, unless a commit updates the baseline on purpose. That
    shows up in the PR diff, where a reviewer sees it.

### 9.4 Exit codes

| Code | Meaning |
|---|---|
| 0 | no blocking findings |
| 1 | blocking findings |
| 2 | usage or configuration error |
| 3 | internal error (rule crash, or a parse failure with `--strict`) |

The terminal summary is generated from the same `Verdict` object as the exit
code, so they can never disagree again (v0.2.1 bug).

### 9.5 Configuration (`seamscan.toml`)

```toml
[policy]
fail_on_severity = "HIGH"
fail_on_confidence = "MEDIUM"

[rules]
disable = ["SC-TEST-003"]
severity = { "SC-CODE-002" = "LOW" }

[paths]
exclude = ["scripts/legacy/**"]
client = ["src/ui/**"]
server = ["src/workers/**"]

[auth]
primitives = ["requireUser", "withAuth"]
protected_paths = ["app/admin/**"]       # enforced by middleware

[ssrf]
allowlist_checks = ["assertAllowedHost"]

[deps]
min_age_days = 30
min_weekly_downloads = 100
allow = ["@internal/*"]
```

Unknown keys are an error (exit 2). Typos in config must not silently disable
rules.

---

## 10. Output formats

| Format | Flag | For |
|---|---|---|
| Terminal | default | humans; grouped by file, colored, with a summary line from `Verdict` |
| JSON | `--format json` | tools; schema `schemas/findings.v1.schema.json`, `schema_version: 1` |
| SARIF 2.1.0 | `--format sarif` | GitHub code scanning |
| Markdown report | `--format md` (audit) | clients; see below |
| Agent | `--format agent` | coding agents; compact, ≤ 8,000 chars |

**SARIF details:**
- Each `runs[0].tool.driver.rules[]` entry has `id`, `shortDescription`,
  `helpUri`, and `properties.security-severity`, which drives GitHub's
  severity labels. The values are CRITICAL 9.5, HIGH 8.0, MEDIUM 5.5,
  LOW 3.0.
- Each result has `ruleId`, `message.text`, a physical location, and
  `partialFingerprints["seamscan/v1"]`. Related locations go in
  `relatedLocations`.
- The output is validated against the official SARIF 2.1.0 schema in tests.
- GitHub's limits apply: 10 MB gzipped, and 5,000 results shown. The audit
  mode caps results and says so.

**Markdown audit report sections:**
1. Summary for a non-technical reader
2. Risk table by severity and category
3. Top findings, each with redacted evidence, why it matters, and how to fix it
4. Everything else, grouped
5. Suppressions and baseline
6. **Method and limits**: what seamscan checks, what it can't, benchmark scores
   with the version, and the files skipped and why

This report is the deliverable for consulting Offer A, so it has to stand on
its own in front of a client.

**Agent format:**
- One line per finding: `path:line [RULE] message → fix`.
- Sorted by severity, then confidence, and capped at the top 20. The cut is
  stated.
- Built for the Claude Code hook's context limits.

---

## 11. Integrations

### 11.1 CLI

```
seamscan scan   [--base REF | --staged | --files PATH...] [--format F] [--offline] [--strict]
seamscan audit  [PATH] [--format F] [--output FILE] [--offline]
seamscan baseline create|prune|check [--against REF]
seamscan rules  [--json]                 # list rules with metadata
seamscan explain RULE-ID                 # print the rule page
seamscan hook claude                     # Claude Code hook adapter (stdin -> stdout)
```

Global: `--config PATH`, `--stats`, `--debug`, `--version`.

### 11.2 GitHub Action (`action.yml`, composite)

The action:
1. Installs uv.
2. Runs `uvx seamscan@<pinned> scan --base ${{ github.event.pull_request.base.sha || 'HEAD~1' }} --format sarif --output seamscan.sarif`.
3. Uploads it with `github/codeql-action/upload-sarif@v4`, category `seamscan`.

The workflow needs `permissions: security-events: write`. v3 of that action
is deprecated in Dec 2026, so v4 only.

Third-party SARIF alerts are eligible for GitHub's Copilot Autofix where the
repo has it enabled. seamscan finds, and GitHub's own tools can propose fixes.

### 11.3 pre-commit

`.pre-commit-hooks.yaml` defines `id: seamscan`, `entry: seamscan scan --staged --offline`,
`pass_filenames: false`.

### 11.4 Claude Code hook

This is an integration, **not a differentiator**. Semgrep Guardian and Snyk
Studio already ship hooks. Its value is that seamscan's rules target AI
failure modes and the stacks AI tools build.

`seamscan hook claude` reads the hook JSON on stdin and branches on
`hook_event_name`:

- **`PostToolUse`** (matcher `Edit|Write|MultiEdit`) or **`PostToolBatch`**:
  - Scans only the edited files, with the offline rules only. Budget: ≤ 1 s.
  - New blocking findings come back as
    `{"hookSpecificOutput": {"hookEventName": "...", "additionalContext": "<agent format>"}}`.
    This doesn't block. The agent sees the findings and can fix them.
- **`Stop`**:
  - Scans the session's changes against `HEAD`.
  - If there are blocking findings, it returns
    `{"decision": "block", "reason": "<agent format>"}` so the agent continues
    and fixes them.
  - If the input has `stop_hook_active: true`, it returns only a
    `systemMessage` for the user. That prevents loops.
- **Errors:** they go to stderr with a non-blocking exit code. A broken
  scanner must never trap the agent.

The docs give a copy-paste `settings.json` snippet.

---

## 12. Engineering quality gates for seamscan itself

### 12.1 CI jobs (all required)

1. `ruff check` + `ruff format --check`
2. `pyright --strict` on `src/`
3. `pytest`, with coverage ≥ 90% on `rules/`, `facts/` and `policy/`. These
   are targeted floors, not a vanity global number.
4. Architecture test (layer contracts, §5.3)
5. The bench job (§8.6), plus the README table staleness check
6. Determinism: run `audit --format json` twice on the fixture repo and check
   the outputs are byte-identical
7. Performance (§13)
8. Self-scan: `seamscan audit .` reports zero blocking findings
9. Schema: JSON output validated against `findings.v1`, SARIF against SARIF
   2.1.0, with snapshot tests for both

### 12.2 Definition of done for a rule

- Benchmark cases are written **first** and fail (TDD).
- The rule is implemented.
- `docs/rules/<ID>.md` exists, with these sections: what, why, examples (TP
  and HN), how to fix, known false positives and negatives, and references
  (CWE, incidents).
- A registry test enforces that every registered rule has a docs page and at
  least 5 positive and 5 negative benchmark cases.
- The rule meets its budget on `dev`.

### 12.3 Dependencies

| Package | Why stdlib or existing deps won't do |
|---|---|
| `typer` | already used; the CLI layer |
| `tree-sitter`, `tree-sitter-typescript`, `tree-sitter-javascript` | no TS/JS parser in the stdlib |
| dev: `pytest`, `ruff`, `pyright` | standard |
| dev: `jsonschema` | validates JSON/SARIF output in tests |

HTTP goes through `urllib`, config through `tomllib` and JWT payloads through
`base64` + `json`. None of those need a dependency. The package uses
`requires-python >= 3.11` for `tomllib`.

---

## 13. Performance budgets

These are measured on a fixed fixture repo, and CI runs with 2× slack.

| Operation | Budget |
|---|---|
| Hook scan of ≤ 5 edited files | ≤ 1.0 s |
| `scan` of a 50-file PR, offline | ≤ 3 s |
| `audit` of 100k lines, offline | ≤ 30 s, ≤ 500 MB RSS |

- **Parsing is the cost center:** each file is parsed once, and every rule
  shares that parse.
- **Queries are compiled once** per process.
- **No per-rule file reads.** Every rule works from the shared parse.
- **Network:** online dependency checks are excluded from these budgets and
  reported separately (requests are sequential and cached).

---

## 14. Milestones

Each milestone ends with its "done when" checks passing in CI.

| # | Milestone | Done when |
|---|---|---|
| **M0** | **Repair and spikes** | `src/` layout; `uvx --from . seamscan --help` works from a fresh clone; MIT `LICENSE`; committed output folders removed; the verdict/exit-code contradiction fixed in v0.2.x so the public README is true. Spikes written up as ADR-001 (SQL parsing), ADR-002 (scan-mode scoping) and ADR-003 (tree-sitter 0.26 TS/TSX queries). `CLAUDE.md` points to this spec. |
| **M1** | **Core and benchmark harness** (until the new engine beats v0.2.x on the benchmark at the end of M2, the `seamscan` command stays the legacy CLI and the new one runs as `python -m seamscan`) | `model`, `workspace`, `parse/python`, the rule protocol, `policy/verdict`, and the JSON and terminal reporters; bench runner and scorer; the v0.2.1 detectors run through the bench, giving a recorded **"before" score**; the determinism test passes. |
| **M2** | **Python rules** | SEC-001/003/004, CODE-001–010 and TEST-001–003 (pytest) meet their budgets. Suppressions work. |
| **M3** | **TS/JS** | The tree-sitter layer, the same rules for TS/JS, WEB-001–003 and file roles (§5.6). TS/JS cases make up ≥ 40% of the corpus. |
| **M4** | **Supabase and Firebase** | Schema replay; SUPA-001–004, FIRE-001 and SEC-002; ≥ 60 original cases, including the CVE-2025-48757 pattern end to end. |
| **M5** | **Dependencies** | The registry client, cache, offline snapshot and DEP-001–003, with network failure behavior tested. |
| **M6** | **Gating and integrations** | Baseline and ratchet; SARIF with GitHub upload verified on a test repo; the Action, pre-commit and the Claude hook; the markdown audit report. |
| **M7** | **Evaluation and release** | Holdout scored; the 20-repo noise study; the comparator run; generated README table; write-up; demo GIF; PyPI 1.0.0. |

Order rationale:
- **M1 first:** the measuring stick comes before the rules.
- **M3 and M4 before M5:** the vibe-coded stack is the differentiator,
  while dependency checks are the most crowded area.

---

## 15. Open questions (for Aaron)

1. ~~Name~~ Decided 2026-10-07: **seamscan**. It names the differentiator, scanning the seams between layers. It was free on PyPI and npm, with no GitHub repos using the name.
2. ~~License~~ Decided: MIT.
3. **LLM-generated corpus:** which models, how many cases, and what spend
   cap? A suggestion: 2–3 current models × 20 task prompts.
4. **Comparisons with Semgrep and Opengrep.** Running them is allowed for
   internal use. *Publishing* numbers from the Semgrep registry rules needs the
   license checked first. Should we skip it, or use Opengrep with community
   rules that have a clear license?
5. **Where the write-up lives:** a personal blog, dev.to, or a GitHub Pages
   page in this repo?

---

## 16. What this demonstrates (portfolio framing)

- **To employers:**
  - static analysis on real syntax trees in two languages
  - cross-file program facts
  - an evaluation method with a holdout set and budgets in CI
  - clean layering enforced by tests
  - SARIF and GitHub integration
  - agent integration
  - honest measurement, including the v0.2.1 "before" score
- **To consulting clients:** the tool behind the "prototype to production"
  audit, and the report they receive.
- **Numbers to quote once they exist:**
  - per-category precision and recall (dev and holdout)
  - findings per 1,000 lines on 20 real repos, with triaged precision
  - recall before (v0.2.1) vs after (v1.0)
  - scan latency

---

## Changelog

- 2026-10-07: M2 infrastructure: file roles, secret classification and redaction, taint-lite string helper, inline suppressions (SC-META-001), scan-mode benchmark cases, budget check, CI workflow with SHA-pinned actions. Added the independent-holdout requirement (§8.3).
- 2026-10-07: M1 done. Core pipeline, policy, JSON/terminal reporters, `scan`/`audit` (via `python -m seamscan`), benchmark harness, 44-case seed corpus, SC-CODE-001 (Python) as the first rule at 6/6 recall and no false alarms. Legacy before-score recorded in §2.
- 2026-10-07: M1 additions: pure `analysis.py`; in-house architecture test replaces import-linter; fake-secret placeholders in cases; hash-derived splits enforced; legacy CLI stays default until the new engine beats it.
- 2026-10-07: Renamed clogbot → seamscan; rule ID prefix CB- → SC-.
- 2026-10-07: M0 spikes done. ADR-001: no sqlglot (in-house SQL statement scanner). ADR-002: cross-file findings are in scan scope if either side changed. ADR-003: tree-sitter 0.26 query API confirmed on TSX.
- 2026-10-07: Draft 1. Positioning informed by landscape research the same
  day: no open offline tool links Supabase/Firebase config to client code;
  the Claude hook isn't a differentiator; the Semgrep rules license blocks
  rule reuse.
