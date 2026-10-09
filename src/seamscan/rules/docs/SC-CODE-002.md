# SC-CODE-002 — Swallowed exception

**Severity:** MEDIUM, raised to HIGH around writes, payments and auth · **Confidence:** HIGH · **CWE:** [CWE-390](https://cwe.mitre.org/data/definitions/390.html) · **Languages:** Python, TypeScript/JavaScript

## What it finds

### Python

A broad `except` handler that throws the error away:

- the handler catches everything: bare `except:`, `except Exception:`,
  `except BaseException:`, or a tuple that contains one of them
  (`except (KeyError, Exception):`), including `except*`
- and its body does nothing but `pass`, `...`, `continue`, `return` or `return None`,
  so there is no logging, no re-raise and no fallback value

The finding is raised to **HIGH** when the `try` block calls something whose failure
should never be silent. The list is short and explicit:

- any `stripe.*` call
- a call through a payment resource: `.charges.`, `.refunds.`, `.payment_intents.`,
  `.payouts.`, `.transfers.`, `.subscriptions.`
- a write method: `commit`, `save`, `insert`, `insert_one`, `insert_many`, `update`,
  `update_one`, `update_many`, `upsert`, `delete`, `delete_one`, `delete_many`,
  `execute`, `executemany`, `bulk_create`, `bulk_update`
- a function or method whose name contains `auth`, `login`, `verify`, `charge` or
  `refund`

Not flagged: a handler with a comment that gives a reason, on the `except` line or in
its body (`except Exception:  # HEIC support is best-effort`), as in JS below. A comment
mentioning `TODO`, `FIXME`, `XXX`, `implement`, `for now`, `placeholder` or `stub` is not
a reason, and neither is a bare tool directive (`noqa: BLE001`, `pragma: no cover`,
`type: ignore`, `nosec`, `pylint: disable=…`). Test files are skipped.

### TypeScript and JavaScript

Every JS `catch` is broad, so the question is only what the handler does.

**A `try`/`catch` whose `catch` block does nothing:** it is empty (comments aside), or
holds only `return`, `return null`, `return undefined` or `continue`. MEDIUM, or HIGH
when the `try` block makes a sensitive call (below).

**A `catch` block that only writes to the console** (`console.log`, `.info`, `.debug`,
`.trace`, `.error`, `.warn`, optionally followed by one of the statements above):
flagged **only when the `try` block makes a sensitive call and the code carries on**,
at HIGH. Elsewhere it counts as logging, the way `logger.warning(...)` does in Python.
The code carries on when something runs after the `try` statement: a later statement
at any enclosing level of the function (a bare `return;` doesn't count), the next turn
of an enclosing loop, or the caller of a function whose result is used. A function
that just ends after logging is not a finding when nobody acts on its outcome: a
callback handed to a call (`socket.on("join", async () => …)`, `cron.schedule(…)`,
`router.post(…)`) or written inline in JSX, an event handler named `handle…` or `on…`,
or a Next.js route export (`GET`, `POST`, …). There the failed call simply isn't
followed by its success step: the user stays on the login page, the broadcast isn't
sent. A named helper or method (`async function forwardOrder(order)`) still counts,
because its caller carries on as if the call worked.

**A promise `.catch(handler)`** whose handler does nothing or only logs
(`() => {}`, `() => null`, `() => undefined`, `(e) => console.error(e)`,
`console.error` passed directly): flagged **only when the chain makes a sensitive
call**, at HIGH, and only when the settled value is thrown away or handed straight back
(`p.catch(…);`, `await p.catch(…)`, `return p.catch(…)`, an arrow's body, also through
a trailing `.finally(…)`). Assigned or passed on, `.catch(() => null)` is a fallback
value (`const body = await req.json().catch(() => null)`), like an `except` that
assigns one. Writing a no-op handler is an explicit choice, and away from writes it is
nearly always a deliberate fire-and-forget (`audio.play().catch(() => {})`).

**Sensitive calls** (the explicit TS/JS list):

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
- not a hash being fed: `createHash(…).update(x)`, or `hash.update(x)` where
  `hash = createHash(…)` (also `createHmac`, `createCipheriv`, `createDecipheriv`)

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
  a file under a `scripts/`, `script/` or `bin/` directory, or named `test-*`,
  `test_*` or `seed*`
- rethrowing, returning a response or any other value, setting state, calling a
  reporter (`Sentry.captureException`, `toast.error`): anything but the forms above
- test files

### The console decision, measured

A catch that only `console.error`s is the most common error handler in AI-built JS
apps, and it is arguably this rule's target: the program carries on as if nothing
happened. It is also very noisy. On 24 public repositories (19 apps built with Lovable
and 5 Vercel/Supabase starters, about 1.0M lines of TS/JS, pinned commits), treating
every console-only catch like an empty one produced **957** MEDIUM findings; the shipped
rule produces **8** MEDIUM and **56** HIGH. A hand check of a random 15 of the HIGH
findings found 12 real lost writes or silently failing user actions; the misses were a
logout during shutdown, a search API called with POST, and a root-level test script.
The 957 are mostly console-logged failed reads in React components: a spinner that stops
or a list that stays empty. That is a UX problem, not lost data, so the rule keeps to
the case where it matters: a write, payment or login that failed while the code carries
on as if it succeeded.

The 2026-10-09 noise study (20 other public repositories, 102k lines, every finding
triaged by a separate reviewer reading the code) judged **26 of 30** of this rule's
findings false. Most were console-only catches around a write whose handler simply
ended (socket events, click handlers, cron callbacks: the success step is skipped and
nothing pretends otherwise), and broad Python excepts with a comment explaining a
best-effort call. Requiring the code to carry on, and honouring Python comments,
removed 13 of those 26 on that corpus and none of the 4 true findings. What remains
is mostly deliberate best-effort cleanup that says so only in a docstring, and named
helpers called fire-and-forget from timers, which would need call-site analysis.

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
except Exception:  # HIGH: a lost write
    pass

try:
    return json.load(f)
except:  # MEDIUM
    return None

except (KeyError, Exception):
    continue
```

Not flagged:

```python
except FileNotFoundError:          # a narrow, expected error
    pass
except Exception:
    logger.warning("fetch failed", exc_info=True)
    return None
except Exception as exc:
    raise HTTPException(500) from exc
except Exception:
    return False                   # a real answer, not silence
except Exception:
    failed += 1
    continue
```

TypeScript and JavaScript, flagged:

```ts
try {
  await supabase.from("orders").insert(order);
} catch (error) {                 // HIGH: only logs a failed write, then redirects
  console.error("Failed to create order:", error);
}

try { setItems(JSON.parse(saved)); } catch {}            // MEDIUM

fetch("/api/checkout", { method: "POST", body }).catch(() => {});   // HIGH
```

Not flagged:

```ts
} catch (err) {
  console.error("Failed to load posts", err);  // a read, logged
} finally { setLoading(false); }

const body = await request.json().catch(() => null);   // a fallback value
if (!body) return NextResponse.json({ error: "Invalid body" }, { status: 400 });

} catch (error) {
  console.error(error);
  return NextResponse.json({ error: "Failed" }, { status: 500 });
}

audio.play().catch(() => {});                  // fire-and-forget, nothing written
} catch { /* non-fatal: the chat keeps its default title */ }
```

## How to fix

Catch the specific exception you expect. If you really mean "anything", log it
(`logger.exception(...)`) or report it (`sentry_sdk.capture_exception()`), and re-raise
when the caller needs to know. Don't wrap writes or payments in a handler that hides
failure.

## Known gaps

- `contextlib.suppress(Exception)` is not flagged, though it swallows the same way.
- A handler that returns any value other than `None` (`return {}`, `return []`) is not
  flagged, even when that value hides the failure just as well.
- A handler that calls something unrelated (`print(...)`, `cleanup()`) counts as doing
  something, so it is not flagged.
- The HIGH list goes by name, so `dict.update` or `cache.delete` in the `try` block
  raises severity too, and a write through a custom helper (`persist(order)`) doesn't.
- An intentional "best effort" handler (`except Exception: pass` around removing a temp
  file) is still flagged; suppress it with a reason.

TS/JS:

- A console-only catch around a read is not flagged, even when the failure leaves the
  user looking at a stale or empty page. That is the measured trade-off above.
- Supabase and many fetch wrappers don't throw: they return `{ error }`. Ignoring that
  `error` is the most common way AI-built Supabase apps lose writes, and it isn't a
  `catch`, so this rule doesn't see it.
- The sensitive list goes by name, as in Python: `map.delete(k)`, `params.delete(k)` or
  `cache.delete(k)` raise severity, and a write through an app helper
  (`saveVerification(...)`, `persist(order)`) doesn't. A read sent as POST (many search
  and LLM APIs) counts as a write.
- A `.then(onOk, () => {})` rejection handler is not checked, only `.catch`.
- A CLI script outside the recognised directories and names reports through the
  console like any other, so its console-only catches around writes are flagged.
- Any comment other than a TODO-style one exempts the block, including a lazy
  `// ignore`.
- `return null` from a function that declares `| null` hides the difference between
  "not found" and "the database is down".

## References

- CWE-390: Detection of Error Condition Without Action
