# SC-CODE-002 — Swallowed exception

**Severity:** MEDIUM, raised to HIGH around writes, payments and auth · **Confidence:** HIGH · **CWE:** [CWE-390](https://cwe.mitre.org/data/definitions/390.html) · **Languages:** Python (TS/JS planned in M3)

## What it finds

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

Test files are skipped.

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
except Exception:          # HIGH: a lost write
    pass

try:
    return json.load(f)
except:                    # MEDIUM
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

## References

- CWE-390: Detection of Error Condition Without Action
