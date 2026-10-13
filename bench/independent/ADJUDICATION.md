# Adjudication of the 41 disagreements (independent split)

Verdicts judge the author's label against the rule page in `src/seamscan/rules/docs/` (plus `kit/CONCEPTS.md` for file roles). They do not judge whether seamscan is right in some other sense.

Totals: **seamscan-wrong 34**, **label-wrong 6**, **page-ambiguous 1**.  One label-wrong verdict was reverted on 2026-10-14 after a spec change (ind-test003-py-unittest-skiptest-in-setup).

| case id | rule | verdict | reason (page quote) |
|---|---|---|---|
| ind-code001-py-aiohttp-ssl-false | SC-CODE-001 | seamscan-wrong | `session.get(url, ssl=False)` on an `aiohttp.ClientSession` turns off verification, which is what the rule is for ("Code that turns off certificate verification for an outbound connection"). The page admits the miss: "Methods on session objects ... are missed, because the receiver's type isn't tracked". The case isn't tagged [known-gap], but its label is right. |
| ind-code001-py-known-gap-session-method | SC-CODE-001 | seamscan-wrong | Known gap: "Methods on session objects (`s = requests.Session(); s.get(url, verify=False)`) are missed". The label is right. |
| ind-code001-ts-known-gap-deno-env-set | SC-CODE-001 | seamscan-wrong | Known gap: "`Deno.env.set("NODE_TLS_REJECT_UNAUTHORIZED", "0")` are not flagged". The label expects it on the line it sits on. |
| ind-code002-py-known-gap-suppress | SC-CODE-002 | seamscan-wrong | Known gap: "`contextlib.suppress(Exception)` is not flagged, though it swallows the same way." The `with suppress` line is line 8. |
| ind-code002-ts-known-gap-custom-helper | SC-CODE-002 | seamscan-wrong | Known gap: "a write through an app helper (`saveVerification(...)`, `persist(order)`) doesn't [count as sensitive]". The case is a console-only catch around exactly that write in a non-script server file, expected on the `catch` line, the same line the page's own TS example marks. |
| ind-code003-py-known-gap-can-edit-true | SC-CODE-003 | seamscan-wrong | Known gap: "guard names outside the word list (`is_admin`, `can_edit`, `is_valid`)" are missed. The label is anchored at the `def`, as the page specifies. |
| ind-code003-ts-known-gap-context-default | SC-CODE-003 | page-ambiguous | Two sentences on the page conflict. "Not flagged: an arrow under an object key (`validateStatus: () => true` ..., or a context's default value): usually a library option, not the app's own check" calls this exempt by design. Known gaps says "`createContext({ checkAccess: () => true })` is missed", which calls it a false negative. |
| ind-code004-py-known-gap-auth-name | SC-CODE-004 | seamscan-wrong | Known gap: "Values named outside the list (`auth == "..."` ...) are missed". The literal `"Bearer prod-static-…"` is not an exempt scheme word. |
| ind-code004-ts-known-gap-switch-case | SC-CODE-004 | seamscan-wrong | Known gap: "`switch (password) { case "admin123": … }` ... are not checked." The label (line 3) is within tolerance of the switch and the case. |
| ind-code005-ts-exp-only-refresh-timing | SC-CODE-005 | seamscan-wrong | The page says these are not flagged: "Reads of only `exp`, `iat`, `nbf` or `header`. Checking whether our own access token needs a refresh ... isn't an auth decision." Its own not-flagged example, `const { exp } = jwt.decode(ourAccessToken) as JwtPayload; // refresh timing`, is this case. Refresh timing has to compare `exp`, so the exemption covers the `if (!exp)`. |
| ind-code006-py-literal-conditions-join | SC-CODE-006 | seamscan-wrong | The page says inert includes "`" AND ".join(conditions)`, where every `conditions.append(...)` is a literal fragment", and "a name assigned only such values". `where` is that join `or "TRUE"`, so only literals reach the SQL text, and the values go in as params. Note: `x or "literal"` is not named on the page explicitly, but nothing on the page suggests it adds a value. |
| ind-code008-ts-server-jsdom-innerhtml | SC-CODE-008 | label-wrong | The page says innerHTML is checked "in client **and unknown-role** files. Server files are skipped". Under CONCEPTS §5.6, a top-level `server/scrape/clean.ts` matches no server rule (no directive, no Next.js convention, no `supabase/functions`, not Python), so it is **unknown**, not server. `html` is a non-inert parameter. Correct label: SC-CODE-008 expected at `server/scrape/clean.ts:6`, not forbidden. |
| ind-code010-py-escape-sequences-only | SC-CODE-010 | label-wrong | The case doesn't contain what its description claims. A byte check shows the file holds the **raw** characters U+202A/U+202E/U+2066/U+2069 (bytes `e2 80 aa` …), with no `\u` escapes at all. The page flags "Bidirectional controls anywhere ... MEDIUM inside a string literal". Correct label: SC-CODE-010 expected at `sanitize/bidi.py:3`. The raw zero-width characters on line 4 sit inside a string, so they are correctly not flagged. |
| ind-code010-ts-escapes-in-regex | SC-CODE-010 | label-wrong | Same problem: the regex literal holds the raw bidi characters, not escapes (no backslashes in the file). The page says a regex literal counts as a string literal, so this is MEDIUM. Correct label: SC-CODE-010 expected at `lib/sanitize.ts:1`. |
| ind-fire001-known-gap-signedin-and-testmode | SC-FIRE-001 | seamscan-wrong | Known gap: "a test-mode or signed-in check joined with something else by `&&`: `request.auth != null && request.time < timestamp.date(...)` on `/{document=**}` is not reported." The label points at the `allow` line, as the page says findings do. |
| ind-meta004-py-index-url-private-404 | SC-META-004 | seamscan-wrong | The page reports "the public registry says 404, but the repository configures another registry for it (... `--index-url` ...)". Line 3 is the dependency's declaration line, which is where SC-DEP-001 says dependency findings point. |
| ind-meta004-py-poetry-source-private-404 | SC-META-004 | seamscan-wrong | Same sentence, which lists "`[[tool.poetry.source]]`". The label points at the declaration line 8. |
| ind-meta004-py-uv-index-private-404 | SC-META-004 | seamscan-wrong | Same sentence, which lists "`[[tool.uv.index]]`". The label points at the declaration line 6. |
| ind-meta004-ts-npmrc-global-registry | SC-META-004 | seamscan-wrong | Same sentence, which lists "`.npmrc` `registry=`". The label points at the declaration line 6. |
| ind-meta004-ts-npmrc-scope-mapping | SC-META-004 | seamscan-wrong | The page's own example is this case word for word: "Couldn't check @acme/design-tokens on npm: npm has no such package, but .npmrc maps @acme to another registry." (Cross-page tension, outside this rule's page: SC-DEP-001 lists "scopes the repository maps to another registry" under "Never looked up, so never reported", yet also says such a package "is SC-META-004, not this rule".) |
| ind-sec001-ts-known-gap-key-in-comment | SC-SEC-001 | seamscan-wrong | Known gap: "Comments are not read, so a key pasted into a ... `// e.g.` comment is missed." `src/server/…` is not client (§5.6 excludes `server/`), so the key falls to SEC-001. |
| ind-sec002-ts-vite-src-stripe-test-literal | SC-SEC-002 | label-wrong | SEC-002 covers "`src/**` of a Vite/CRA/Expo app outside its `server/`, **`api/`** and `functions/` folders". `src/api/payments.ts` is inside `api/`, so it is not a client file, and SEC-001 says it reports "server and unknown-role TS/JS files". Correct label: SC-SEC-001 (LOW, test-mode key) expected at `src/api/payments.ts:1`, and no SC-SEC-002. |
| ind-sec003-py-known-gap-default-in-constant | SC-SEC-003 | seamscan-wrong | Known gap: "A default held in a variable or built at runtime (`os.getenv("X", DEFAULT)`) is missed." `INTERNAL_API_TOKEN` ends in `TOKEN`. |
| ind-sec003-ts-known-gap-ternary-fallback | SC-SEC-003 | seamscan-wrong | Known gap: "a fallback through a ternary (`process.env.X ? process.env.X : "dev"`) ... is missed." |
| ind-sec004-env-known-gap-staging-name | SC-SEC-004 | seamscan-wrong | Known gap: "Other names are not checked: `.env.staging`, ...". Line 1 is "a URL with a password in it", and the finding sits at "the first real sensitive value". |
| ind-test001-py-helper-in-other-module | SC-TEST-001 | seamscan-wrong | Known gap: "A helper called `run_case` in `tests/helpers.py` that asserts looks like no assertion (false positive)." The page calls it a false positive, so the forbidden label is right. |
| ind-test001-ts-assertion-forms-ok | SC-TEST-001 | seamscan-wrong | The flagged test is the page's own not-flagged example, `expect(render(<PriceTag cents={1999} />).container).toMatchSnapshot()`, and the page counts snapshot matchers and any `expect…` chain as assertions. **Caveat:** the case puts JSX in `users.test.ts` (not `.tsx`), which is not valid TypeScript. That is likely why seamscan lost the assertion. Recommend renaming the file to `.tsx` and re-running before counting this case. |
| ind-test001-ts-nock-done-only | SC-TEST-001 | seamscan-wrong | Known gap: "nock's `scope.done()` ... are not recognized, so a test that only calls one of them is flagged (false positive)." |
| ind-test001-ts-not-run-and-no-throw-titles | SC-TEST-001 | label-wrong | The page says "`test.step` ... [is] not [a test]", but the enclosing `test("visits the page")` is a test, and its title isn't a no-crash title. Its only candidate check is `locator.waitFor()`, which is not on the page's closed list of implicit checks ("`waitForURL`, `waitForSelector`, `waitForElementToBeRemoved`"). The page also says "`page.getByText(...)` never counts", and flags its own Playwright example that only drives locators. Correct label: SC-TEST-001 expected at `e2e/billing.spec.ts:8`. The rest of the case (todo, skip, xit, fixme, hooks, no-crash titles) stays forbidden. |
| ind-test002-py-known-gap-nan-check | SC-TEST-002 | seamscan-wrong | Known gap: "`assert x == x` used as a "not NaN" check is flagged (false positive)." |
| ind-test002-py-known-gap-via-variable | SC-TEST-002 | seamscan-wrong | Known gap: "Tautologies that go through a variable (`expected = total; assert total == expected`) are missed." The label is on the assertion line, as the page says. |
| ind-test002-ts-known-gap-chai-property-true | SC-TEST-002 | seamscan-wrong | Known gap: "chai's property assertions (`expect(true).to.be.true` ...) are not evaluated, so tautologies written that way are missed." |
| ind-test002-ts-known-gap-nan-assert | SC-TEST-002 | seamscan-wrong | Known gap: "`assert(x === x)` used as a "not NaN" check is flagged (false positive)." |
| ind-test003-py-known-gap-rename-disables | SC-TEST-003 | seamscan-wrong | Known gap: "Disabling by renaming (`def test_x` → `def _test_x` ...) ... is missed." |
| ind-test003-py-known-gap-string-skipif | SC-TEST-003 | seamscan-wrong | The decision says "platform and version conditions are fine". Known gap: "The old string form `skipif("sys.platform == 'win32'")` is not evaluated, so it is flagged even when the condition is a platform check." So the forbidden label is right. |
| ind-test003-py-unittest-skiptest-in-setup | SC-TEST-003 | label-wrong | The rule fires only "In a test file". The documented Python test-file patterns are "`test_*.py`, `*_test.py`, `conftest.py` and anything under `tests/` or `test/`" (SC-TEST-001; CONCEPTS §5.6 says the same), and Django's `orders/tests.py` matches none of them. The page also says a skip "in a non-test module ... is not flagged". Correct label: no SC-TEST-003 finding. If Django `tests.py` should count, the docs need to change first. **Reverted 2026-10-14:** spec §5.6 now counts Django's `tests.py` as a test file, so the author's label (expected at `orders/tests.py:8`) is restored. |
| ind-test003-ts-known-gap-imported-platform-flag | SC-TEST-003 | seamscan-wrong | Known gap: "a skip gated on a value from another module (`skipIf(isWindows)` with `isWindows` imported) is flagged even when that value is a platform check (false positive)." |
| ind-web001-known-gap-unrelated-getuser | SC-WEB-001 | seamscan-wrong | Known gap (false negatives): "A call named like an auth primitive is trusted, even an unrelated `db.getUser(id)`." The 404 is not a 401/403, and line 10 is the first write. |
| ind-web001-py-known-gap-intermediate-getuser | SC-WEB-001 | seamscan-wrong | `db.get_user` matches the primitive `getUser` (the page compares names "lowercased without underscores"), which is the admitted gap above. Line 11, `db.session.add`, is the first write, which is where "The finding points". |
| ind-web002-known-gap-denylist-localhost | SC-WEB-002 | seamscan-wrong | Known gap: "Any hostname comparison counts, including a denylist (`u.hostname !== "localhost"`)". The label sits at the `fetch` sink. |
| ind-web002-py-host-port-from-json | SC-WEB-002 | seamscan-wrong | The page's flagged example is this case: "`r = requests.get(f"http://{host}:{port}/status")  # host from the JSON body`". `request.get_json()` is a listed source, and taint follows "destructuring", index access and `.get` on a tainted value. |

## What was done with these verdicts (2026-10-09)

- **label-wrong (6):** relabelled as the verdict says, except the two SC-CODE-010
  cases: their descriptions promise escape sequences but the files held the raw
  characters, so the files now hold the escapes (the author's intent) and stay negative.
- **ind-test001-ts-assertion-forms-ok:** JSX in a `.ts` file doesn't compile, so the file
  is renamed `.tsx`; the label is unchanged.
- **page-ambiguous (1)**, and **ind-meta004-ts-npmrc-scope-mapping** (the pages
  contradict each other, as the caveat notes): labels kept as the author wrote them and
  counted against seamscan. The pages get fixed for the next version.
- **seamscan-wrong (34):** counted as written. A rule fix that uses one of these cases
  moves the case to `bench/cases/` under a new id.
- Separately, four SC-META-004 cases failed only because the harness skipped the CLI's
  rule that a public 404 is inconclusive when the repository uses another registry; the
  harness now applies it (commit "Treat a public 404 as inconclusive...").

## Re-adjudication after the second noise pass (2026-10-09)

SC-CODE-002, SC-SEC-003 and SC-WEB-003 were narrowed (ADR-005 era). Nine cases written
under the old pages newly disagreed. A fresh adjudicator judged them against the new
pages only:

| case id | rule | verdict | reason |
|---|---|---|---|
| ind-code002-ts-json-parse-empty-catch | SC-CODE-002 | label-wrong | The `try` only parses and sets React state, with no state-changing call, and the page lists this exact line as not flagged: "`try { setItems(JSON.parse(saved)); } catch {}            // a read`" ("without one, nothing is reported"). |
| ind-sec003-py-setdefault-db-password | SC-SEC-003 | page-ambiguous | The Decision says DB credentials are not reported ("A name is such a credential when one of its words names a service: … `DB` … Those are not reported"), yet the page's own Flagged example is this exact line: "`os.environ.setdefault(\"DB_PASSWORD\", \"postgres\")`". |
| ind-web003-py-fastapi-cors-wildcard-credentials | SC-WEB-003 | label-wrong | The repo (one file: `app/main.py`, a notes API) has no cookie, session or basic-auth use, and "the CORS shapes above are reported only when the repository shows ambient credentials somewhere". |
| ind-web003-ts-express-options-const-wildcard-list | SC-WEB-003 | label-wrong | `server/app.ts` is the only file and has no cookie, `express-session`, `cookie-parser` or basic auth, so "reported only when the repository shows ambient credentials somewhere" excludes it. |
| ind-web003-ts-fastify-register-cors | SC-WEB-003 | label-wrong | `src/app.ts` is the only file and shows no ambient credentials, so "reported only when the repository shows ambient credentials somewhere" excludes it. |
| ind-web003-ts-hono-cors-wildcard-credentials | SC-WEB-003 | label-wrong | `src/index.ts` is the only file; its `/api/session` route returns `{ ok: true }` and uses no session library or cookie, so "reported only when the repository shows ambient credentials somewhere" excludes it. |
| ind-web003-ts-next-config-headers-list | SC-WEB-003 | label-wrong | `next.config.js` is the only file and shows no ambient credentials, so "reported only when the repository shows ambient credentials somewhere" excludes it. |
| ind-web003-ts-route-handler-header-object | SC-WEB-003 | label-wrong | `app/api/session/route.ts` is the only file; despite the folder name it never calls `cookies()`, sets a cookie or uses a session library, so "reported only when the repository shows ambient credentials somewhere" excludes it. |
| ind-web003-ts-vercel-json-headers | SC-WEB-003 | label-wrong | `vercel.json` is the only file and shows no ambient credentials, so "reported only when the repository shows ambient credentials somewhere" excludes it. |

Notes:

- **Known-gap check (SC-WEB-003).** The page lists as a false negative "Cookies that something outside the repository sets for the API's site … so a credentialed wildcard policy in a repository that never mentions cookies goes unreported." I did not count that as a gap miss here. It only applies when such outside cookies actually exist, and none of these cases shows an outside auth service, gateway or proxy. The two `/api/session` cases (Hono, Next route handler) come closest: the path name hints at a session kept somewhere else. But a path name is not one of the page's listed signals, so I still call them label-wrong.
- **SC-SEC-003 conflict.** The Known gaps entry ("A local Postgres started with `POSTGRES_PASSWORD=postgres` accepts a `\"postgres\"` fallback; … it isn't reported (false negative)") backs the Decision over the example: it describes not reporting this as intended, with a known downside. The case has no compose file or other sign of such a Postgres, so the gap doesn't turn this into a seamscan error. The stale Flagged example is a doc bug. Once it is fixed (for example, swapped for `SECRET_KEY`), this becomes label-wrong.

Done with the verdicts: the 8 label-wrong cases are relabelled (expected became
forbidden); the page-ambiguous SC-SEC-003 case keeps its label and counts as a miss,
and the page's stale Flagged example (a DB password) moved to Not flagged. The
independent set now under-tests SC-WEB-003's narrowed positive (cookies present):
none of its remaining WEB-003 positives was written for it.
