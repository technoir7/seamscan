# SC-CODE-003 — Unfinished code in a shipped path

**Severity:** HIGH · **Confidence:** HIGH · **CWE:** [CWE-1164](https://cwe.mitre.org/data/definitions/1164.html) · **Languages:** Python, TypeScript/JavaScript

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
- `raise NotImplementedError("…")` with a message, inside an `if`/`elif`/`else` branch or
  a `match` case: a branch that names the input it rejects after handling the supported
  ones (`else: raise NotImplementedError(f"Unknown database engine {engine}")`), like
  the TS/JS template-message exemption below. A message that says the work isn't done
  (`not implemented`, `not yet implemented`, `unimplemented`, `TODO`) and a bare
  `raise NotImplementedError` in a branch are still flagged.
- health and liveness probes: a guard name that also has the word `health`, `healthz`,
  `liveness`, `readiness`, `ping`, `alive` or `ready` (`health_check`, `readinessCheck`).
  Returning True is the probe working. This applies to TS/JS too.
- `is_authenticated` returning True: Flask-Login's and Django's user classes define it
  that way on purpose

The class exemptions apply to both forms. The spec only names them for
`NotImplementedError`, but a `return True` hook in a `Base*` class is the same
"override me" default (DRF's own `BasePermission.has_permission` is one).

### TypeScript and JavaScript

- a `throw` of `new Error(…)` (or any `…Error`, with or without `new`) or a bare string
  whose message matches `not implemented`, `not yet implemented` or `unimplemented` in
  any case, or contains the upper-case marker `TODO`; and `throw new
  NotImplementedError()`. "Method not implemented." is what TypeScript's "implement
  interface" quick fix writes. `TODO` must be upper case, so a todo app's `"Todo not
  found"` doesn't count. Anchored at the `throw`.
- a function with a guard name (the same word list as Python) whose body is empty
  (comments aside) or only `return true`, or an arrow whose body is `true`. The name
  comes from a function declaration, a method (also object-literal methods such as
  Auth.js's `callbacks: { authorized() { return true } }`), or the variable an arrow or
  function expression is assigned to. Anchored at that name.

Not flagged:

- a template message with a substitution, `` `Automation type not implemented:
  ${type}` ``: a dispatcher naming the input it rejects, after handling the supported
  ones
- methods of an `abstract class`, of a class whose name has the word `Base` or
  `Abstract`, or overridden by a subclass in the same file (as for Python)
- interface members, overload signatures, `declare function` and `.d.ts` files: they
  have no body
- a stub whose body has a comment giving a reason (`// Always run the middleware above,
  which redirects itself`). A comment mentioning `TODO`, `FIXME`, `XXX`, `implement`,
  `for now`, `placeholder` or `stub` is not a reason.
- a function with a parameter typed `never` (`function exhaustiveCheck(x: never) {}`):
  the type checker does that check
- React event handlers, whose name starts with the word `handle` or `on`
  (`const handleCheck = () => {}`): a UI placeholder, not a security check
- an arrow under an object key (`validateStatus: () => true` in an axios config, or a
  context's default value): usually a library option, not the app's own check
- `return NextResponse.json({ error: "Not implemented" }, { status: 501 })`: a
  deliberate answer, not a throw
- test files

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
    def send(self, user, message):
        raise NotImplementedError


@overload
def check_access(user: User, doc: Document) -> bool: ...


def __eq__(self, other):
    return NotImplemented  # not NotImplementedError
```

TypeScript and JavaScript, flagged:

```ts
async refund(chargeId: string): Promise<void> {
  throw new Error("Method not implemented.");
}

function verifySignature(payload: string, signature: string | null): boolean {
  // TODO: compare HMAC-SHA256 of payload with the X-Signature header
  return true;
}

const isAuthorized = (user: User | null) => true;
```

Not flagged:

```ts
if (!todo) throw new Error("Todo not found");
default: throw new Error(`Automation type not implemented: ${automation.type}`);
export abstract class Notifier { validate(m: string) { return true; } }
export function exhaustiveCheck(_value: never): void {}
const handleCheck = (checked: boolean) => {};
```

## How to fix

Implement the check, or remove the route or feature until it exists. If the function
really is an interface, make that explicit with `@abstractmethod`, a `Protocol`, or an
`ABC` base class.

## Known gaps

- `raise NotImplementedError(f"unsupported provider {p}")` used as an "unsupported
  input" error is flagged when it isn't inside a branch (a dict dispatch's fallback, the
  last line of a function after early returns), though it is often deliberate.
  Suppress it with a reason, or raise `ValueError`.
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

TS/JS:

- Class fields (`verify = () => true`), arrows under object keys and functions passed
  inline are not checked, so `createContext({ checkAccess: () => true })` is missed.
- `return Promise.resolve(true)`, `return !!1` and other always-true shapes are missed.
- A comment that explains a stub exempts it, even when the explanation is wrong.
- A dispatcher whose message has no substitution (`throw new Error("PayPal not
  implemented")`) is flagged, which is usually right but sometimes deliberate.
- Names ending in a guard word that aren't guards are flagged when stubbed
  (`function onboardingCheck() {}` is not exempt, `handleCheck` is).

## References

- CWE-1164: Irrelevant Code
