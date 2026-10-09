# SC-CODE-002 — Swallowed exception

**Severity:** HIGH (MEDIUM for a bare `except:` that only ignores everything) · **Confidence:** HIGH · **CWE:** [CWE-390](https://cwe.mitre.org/data/definitions/390.html) · **Languages:** Python, TypeScript/JavaScript

## What it finds

**Decision: a swallowed error matters when the failed call changes state.** A write, a
payment or a login that fails inside a silent handler leaves the program believing
something happened that didn't. Around anything else (a read with a fallback, a
clipboard copy, opening a browser, parsing a URL) a broad handler is nearly always a
deliberate best effort. So every form below needs a **state-changing call** in the
`try` block (the lists follow); without one, nothing is reported.

### Python

A broad `except` handler that throws the error away around a state-changing call:

- the handler catches everything: bare `except:`, `except Exception:`,
  `except BaseException:`, or a tuple that contains one of them
  (`except (KeyError, Exception):`), including `except*`
- its body does nothing but `pass`, `...`, `continue`, `return` or `return None`,
  so there is no logging, no re-raise and no fallback value
- and the `try` block makes a state-changing call:
  - any `stripe.*` call
  - a call through a payment resource: `.charges.`, `.refunds.`, `.payment_intents.`,
    `.payouts.`, `.transfers.`, `.subscriptions.`
  - a write method: `commit`, `save`, `insert`, `insert_one`, `insert_many`, `update`,
    `update_one`, `update_many`, `upsert`, `delete`, `delete_one`, `delete_many`,
    `execute`, `executemany`, `bulk_create`, `bulk_update`
  - a SQLAlchemy session write on a session-like receiver (`db`, `session`,
    `db_session`, `sess`, `*session`): `add`, `add_all`, `merge`, `flush`,
    `bulk_save_objects`
  - a function or method whose name contains `auth`, `login`, `verify`, `charge` or
    `refund`

`execute` runs whatever it is given, so it doesn't count when it runs a read: a query
builder that only selects (`supabase.table("t").select("*").eq(...).execute()`) or SQL
text starting with `SELECT`, `WITH`, `SHOW` or `EXPLAIN`.

**One form needs no state-changing call:** a bare `except:` or `except BaseException:`
whose body does nothing also swallows KeyboardInterrupt and SystemExit, so the program
can't be stopped cleanly there (a worker's heartbeat loop that ignores Ctrl-C). MEDIUM.

Not flagged: a handler with a comment that gives a reason, on the `except` line or in
its body (`except Exception:  # HEIC support is best-effort`), as in JS below. A comment
mentioning `TODO`, `FIXME`, `XXX`, `implement`, `for now`, `placeholder` or `stub` is not
a reason, and neither is a bare tool directive (`noqa: BLE001`, `pragma: no cover`,
`type: ignore`, `nosec`, `pylint: disable=…`). Test files are skipped.

### TypeScript and JavaScript

Every JS `catch` is broad, so the question is what the handler does, and whether the
`try` block (or the promise chain) makes a state-changing call (the list below).

**A `try`/`catch` whose `catch` block does nothing:** it is empty (comments aside), or
holds only `return`, `return null`, `return undefined` or `continue`.

**A `catch` block that only writes to the console** (`console.log`, `.info`, `.debug`,
`.trace`, `.error`, `.warn`, optionally followed by one of the statements above):
flagged **only when the code carries on** after it. Elsewhere it counts as logging, the
way `logger.warning(...)` does in Python. The code carries on when something runs after
the `try` statement: a later statement at any enclosing level of the function (a bare
`return;` doesn't count), the next turn of an enclosing loop, or the caller of a
function whose result is used. A function that just ends after logging is not a
finding when nobody acts on its outcome:

- a callback handed to a call (`socket.on("join", async () => …)`, `cron.schedule(…)`,
  `router.post(…)`) or written inline in JSX
- an event handler named `handle…` or `on…`, or a Next.js route export (`GET`, `POST`, …)
- a module-private helper that every caller in the file starts and forgets: each call
  is a bare statement without `await` (`startRound(code, io);`) or a callback's body
  (`setTimeout(() => endRound(code), 5000)`)

There the failed call simply isn't followed by its success step: the user stays on the
login page, the broadcast isn't sent. A helper that is exported, passed around, awaited
or whose result is used still counts, because its caller carries on as if the call
worked.

**A promise `.catch(handler)`** whose handler does nothing or only logs
(`() => {}`, `() => null`, `() => undefined`, `(e) => console.error(e)`,
`console.error` passed directly), when the settled value is thrown away or handed
straight back (`p.catch(…);`, `await p.catch(…)`, `return p.catch(…)`, an arrow's body,
also through a trailing `.finally(…)`). A handler that only logs follows the same
"carries on" test as a `catch` block: a Cloud Function trigger that returns the chain
and ends is not a finding. Assigned or passed on, `.catch(() => null)` is a fallback
value (`const body = await req.json().catch(() => null)`), like an `except` that
assigns one.

**State-changing calls** (the explicit TS/JS list):

- a write method, by its last name: `insert`, `insertOne`, `insertMany`, `update`,
  `updateOne`, `updateMany`, `upsert`, `delete`, `deleteOne`, `deleteMany`, `save`,
  `commit`, `execute`. This covers Supabase (`supabase.from("t").insert(…)`), Prisma
  (`prisma.user.update`), Mongo and Knex.
- Prisma's `create`/`createMany` on a client named `prisma`, `db` or `tx`
  (`create` alone is too common: `Object.create`, `axios.create`)
- anything on `stripe` (`stripe.refunds.create`), or through a payment resource:
  `charges`, `refunds`, `paymentIntents`, `payouts`, `transfers`, `subscriptions`
- `fetch(url, { method: "POST" | "PUT" | "PATCH" | "DELETE" })` (any case) and
  `axios.post`/`put`/`patch`
- auth actions: a method on `*.auth.*` that isn't a read (not `get…`/`on…`, so
  `supabase.auth.signInWithPassword` counts and `supabase.auth.getSession` doesn't);
  a call whose name starts with `login`, `logout`, `signIn`, `signUp`, `signOut`,
  `logIn`, `authenticate`, `authorize`, `charge` or `refund`; `verify` itself, or
  `verify…` ending in `Token`, `Id`, `Otp`, `Signature`, `Jwt`, `Password`, `Session`,
  `Email`, `Webhook` or `Code` (`jwt.verify`, `verifyIdToken`)

These don't count, in either language:

- **a write to a log, analytics or audit table**: a word of the table or model name is
  `log(s)`, `analytics`, `telemetry`, `audit`, `pageview(s)`, `metrics` or `impressions`
  (`supabase.from("api_logs").insert(…)`, `AuditLog.objects.create(…)`), the same list
  as [SC-WEB-001](SC-WEB-001.md)'s public writes. Logging is best effort by nature: an
  error logger that falls back to the console is doing its job.
- `createHash(…).update(x)`, or `hash.update(x)` where `hash = createHash(…)` (also
  `createHmac`, `createCipheriv`, `createDecipheriv`): a hash being fed
- (TS/JS) `x.delete(k)` and the like on a name bound to `new Map()`, `new Set()`,
  `new WeakMap()` or `new WeakSet()` in the same module: memory, not stored data

**Not flagged:**

- a block whose comments give a reason: `catch { /* non-fatal: keeps the default
  title */ }`. A comment mentioning `TODO`, `FIXME`, `XXX`, `implement`, `for now`,
  `placeholder` or `stub` doesn't count as a reason. A reviewer reads the comment, so
  it works like a suppression with a reason (Python too, above).
- `return null` (or `undefined`) when null is already one of the function's answers:
  its declared return type includes `null`/`undefined`, or another `return` in it can
  produce null (`return row ?? null`). Callers must handle null anyway, like the
  `return false` of a validator.
- console-only catches in command-line scripts, where the console is how they report:
  a file under a `scripts/`, `script/` or `bin/` directory or any directory whose name
  starts with `seed` (`seed/`, `seeds/`, `seeders/`, `seedData/`), a file named
  `test-*`, `test_*` or `seed*`, or a module that says it runs as a command: a shebang
  (`#!/usr/bin/env node`), `require.main === module`, `import.meta.main`, or
  `import.meta.url` compared with `process.argv[1]`. An empty catch in a script is
  still flagged: it reports nothing to anyone.
- rethrowing, returning a response or any other value, setting state, calling a
  reporter (`Sentry.captureException`, `toast.error`): anything but the forms above
- test files

### Measured

A catch that only `console.error`s is the most common error handler in AI-built JS
apps. On 24 public repositories (19 apps built with Lovable and 5 Vercel/Supabase
starters, about 1.0M lines of TS/JS, pinned commits), treating every console-only catch
like an empty one produced **957** findings; keeping console-only catches to writes,
payments and logins produced 64, and a hand check of 15 of those found 12 real lost
writes or silently failing user actions.

Two later noise studies (40 other public repositories, 240k lines, every finding
triaged by a separate reviewer reading the code; spec §8.4) judged only **5 of 59**
findings true when every broad handler counted, whatever its `try` block did. The false
ones were best-effort reads and conveniences (URL parsing, a clipboard copy, a cache
read, `webbrowser.open`), console-only catches whose handler simply ended (socket
events, click handlers, timers), seed scripts, error loggers writing to a log table,
and select-only queries run through `execute()`. Requiring a state-changing call and the
other rules on this page removed 44 of the 54 false findings on those 40 repositories
and kept 4 of the 5 true ones; the one lost is a refund through a custom model method
(`CreditAccount.grant(...)`) whose name says nothing about writing (see Known gaps).
Those repositories shaped these rules, so they are development data; the published
figure comes from a set pinned before the change.

## Why it matters

When a write, a payment or a login check fails inside a silent handler, the program
carries on as if it worked: the order shows as updated, the refund as issued, the user
as checked. Nobody finds out until the data is wrong. AI assistants often add
`except Exception: pass` to make a traceback go away.

## Examples

Flagged:

```python
try:
    db.session.commit()
except Exception:  # a lost write
    pass

try:
    session.add(Customer(**row))
    session.flush()
except (KeyError, Exception):  # a CSV import that silently drops rows
    continue

while True:
    try:
        r.set(f"worker:{wid}:alive", time.time())
    except BaseException:  # MEDIUM: also swallows Ctrl-C
        ...
```

Not flagged:

```python
except FileNotFoundError:          # a narrow, expected error
    pass

try:
    return urlparse(url).netloc or None
except Exception:                  # a read: nothing is left undone
    return None

try:
    supabase.table("audit_log").insert(event).execute()
except Exception:                  # a log write: best effort by nature
    pass

except Exception:
    logger.warning("fetch failed", exc_info=True)
    return None
except Exception as exc:
    raise HTTPException(500) from exc
```

TypeScript and JavaScript, flagged:

```ts
try {
  await supabase.from("orders").insert(order);
} catch (error) {                 // only logs a failed write, then redirects
  console.error("Failed to create order:", error);
}
redirect("/thanks");

try { await supabase.from("orders").insert({ items }); } catch {}

fetch("/api/checkout", { method: "POST", body }).catch(() => {});
```

Not flagged:

```ts
try { setItems(JSON.parse(saved)); } catch {}            // a read

} catch (err) {
  console.error("Failed to load posts", err);  // a read, logged
} finally { setLoading(false); }

socket.on("join", async ({ code }) => {
  try { await room.save(); io.to(code).emit("joined"); }
  catch (err) { console.error(err); }          // the handler just ends
});

const body = await request.json().catch(() => null);   // a fallback value

audio.play().catch(() => {});                  // fire-and-forget, nothing written
} catch { /* non-fatal: the chat keeps its default title */ }
```

## How to fix

Catch the specific exception you expect. If you really mean "anything", log it
(`logger.exception(...)`) or report it (`sentry_sdk.capture_exception()`), and re-raise
when the caller needs to know. Don't wrap writes or payments in a handler that hides
failure.

## Known gaps

- The state-changing list goes by name. A write through a custom helper or model method
  (`CreditAccount.grant(...)`, `persist(order)`, `saveVerification(...)`) isn't seen, so a
  swallowed failure around it isn't reported; `dict.update`, `params.delete(k)` or
  `cache.delete(k)` count as writes.
- `contextlib.suppress(Exception)` is not flagged, though it swallows the same way.
- A handler that returns any value other than `None` (`return {}`, `return []`) is not
  flagged, even when that value hides the failure just as well.
- A handler that calls something unrelated (`print(...)`, `cleanup()`) counts as doing
  something, so it is not flagged.
- An intentional best-effort write (`except Exception: pass` around deleting a temp
  blob) is still flagged; suppress it with a reason.
- `cursor.execute(sql)` with SQL built elsewhere counts as a write, even when it reads.

TS/JS:

- A console-only catch around a read is not flagged, even when the failure leaves the
  user looking at a stale or empty page. That is the measured trade-off above.
- Supabase and many fetch wrappers don't throw: they return `{ error }`. Ignoring that
  `error` is the most common way AI-built Supabase apps lose writes, and it isn't a
  `catch`, so this rule doesn't see it. A `catch` around such a call is practically
  unreachable, yet it is still reported.
- A curried function (a Redux thunk, `(id) => (dispatch) => { … }`) is treated as if
  its caller acts on the outcome, so a logged `.catch` inside it is reported.
- A read sent as POST (many search and LLM APIs) counts as a write.
- A `.then(onOk, () => {})` rejection handler is not checked, only `.catch`.
- Any comment other than a TODO-style one exempts the block, including a lazy
  `// ignore`.
- `return null` from a function that declares `| null` hides the difference between
  "not found" and "the database is down".

## References

- CWE-390: Detection of Error Condition Without Action
