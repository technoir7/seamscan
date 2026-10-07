# SC-CODE-003 — Unfinished code in a shipped path

**Severity:** HIGH · **Confidence:** HIGH · **CWE:** [CWE-1164](https://cwe.mitre.org/data/definitions/1164.html) · **Languages:** Python (TS/JS planned in M3)

## What it finds

Placeholders that ship in non-test code:

- `raise NotImplementedError` or `raise NotImplementedError(...)` (anchored at the
  `raise`)
- a function whose name contains one of the words `auth`, `authenticate…`,
  `authorize…`, `verify…`, `validate…`, `check`, `permission(s)`, `allowed`, `charge`
  or `refund…`, and whose body (ignoring a docstring) is only `pass`, `...`, nothing, or
  `return True` (anchored at the `def`)

Names are compared word by word (`snake_case`, `camelCase` and `X-Header` style), so
`get_author` and `on_checkbox_toggled` don't count.

Not flagged:

- methods decorated with `@abstractmethod` or `@overload`
- methods of a class that is meant to be overridden: a `Protocol` (also `Protocol[T]`),
  a class deriving from `ABC` or using `metaclass=ABCMeta`, or a class whose name has
  the word `Base` or `Abstract` (`BaseNotifier`)
- a method that a subclass in the same file overrides: the class is an interface
  whatever it is called. A subclass that *inherits* the stub doesn't count, so
  `class StripeProvider(PaymentProvider)` without its own `refund` still leaves the
  base's `raise NotImplementedError` flagged.
- `.pyi` stub files, which are never analyzed
- test files
- `is_authenticated` returning True: Flask-Login's and Django's user classes define it
  that way on purpose

The class exemptions apply to both forms. The spec only names them for
`NotImplementedError`, but a `return True` hook in a `Base*` class is the same
"override me" default (DRF's own `BasePermission.has_permission` is one).

## Why it matters

AI assistants scaffold a function, leave the body for later, and the code ships. A
`verify_signature` that returns `True` accepts forged webhooks. A `check_permission`
that is only `pass` lets everyone through when it's used as a raise-on-failure guard.
A `raise NotImplementedError` in a route is a 500 waiting for the first real user.

## Examples

Flagged:

```python
def verify_signature(payload: bytes, signature: str) -> bool:
    return True

def verify_api_key(x_api_key: str = Header(...)) -> None:
    """Reject requests without a valid API key."""
    pass

def refund(self, payment_intent_id: str):
    raise NotImplementedError()
```

Not flagged:

```python
class SignatureVerifier(Protocol):
    def verify(self, payload: bytes, signature: str) -> bool: ...

class BaseNotifier:
    def send(self, user, message): raise NotImplementedError

@overload
def check_access(user: User, doc: Document) -> bool: ...

def __eq__(self, other):
    return NotImplemented          # not NotImplementedError
```

## How to fix

Implement the check, or remove the route or feature until it exists. If the function
really is an interface, make that explicit with `@abstractmethod`, a `Protocol`, or an
`ABC` base class.

## Known gaps

- `raise NotImplementedError(f"unsupported provider {p}")` used as an "unsupported
  input" error in a dispatcher is flagged, though it is often deliberate. Suppress it
  with a reason, or raise `ValueError`.
- Stubs with other always-true shapes (`return 1`, `return not False`, `return user is
  not None or True`) are missed, and so are guard names outside the word list
  (`is_admin`, `can_edit`, `is_valid`).
- A base class whose subclasses live in other files (common in libraries, rare in app
  code) is flagged unless it is named `Base*`/`Abstract*` or derives from `ABC`.
- An override that deliberately does nothing (`def _check_scope(self, ...): pass  # always
  valid here`) is flagged.
- `NotImplementedError` raised as a signal (from `__len__` to opt out of a protocol, or
  as an "unsupported" error a caller catches) is flagged.
- `TODO`/`FIXME` comments and placeholder return values like `return {}` are out of scope.

## References

- CWE-1164: Irrelevant Code
