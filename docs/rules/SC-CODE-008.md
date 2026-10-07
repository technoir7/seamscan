# SC-CODE-008 — Code or HTML evaluated from non-literals

**Severity:** HIGH · **Confidence:** MEDIUM · **CWE:** [CWE-95](https://cwe.mitre.org/data/definitions/95.html), [CWE-79](https://cwe.mitre.org/data/definitions/79.html) · **Languages:** Python, TypeScript/JavaScript

## What it finds

The builtins `eval`, `exec` and `compile`, also reached as `builtins.eval` and so on,
called with source text that isn't fixed in the source. That means anything other
than a literal, a composition of literals, or a name assigned only literals in its
function or at module level (spec §6.3).

- Restricting globals (`{"__builtins__": {}}`) doesn't make it safe, so it's still
  flagged.
- `exec(compile(src, ...))` is reported once, at the `compile` call. The code object
  isn't reported again.
- Test files are skipped.

Not matched, because they aren't the builtins: `ast.literal_eval`, `re.compile`
(including `from re import compile`), `model.eval()`, `DataFrame.eval`, and
SQLModel's `session.exec`.

### TypeScript and JavaScript: code

- `eval(x)` (also `window.eval`, `globalThis.eval`), `vm.runInThisContext`,
  `vm.runInNewContext`, `vm.runInContext`, `vm.compileFunction` and `new vm.Script`,
  when the code argument isn't inert (spec §6.2).
- `new Function(...)` or `Function(...)` when any argument isn't inert. Parameter names
  are code too.
- `setTimeout`/`setInterval` (bare or on `window`) whose first argument is a string
  visibly assembled from values (template, `+`, `.concat`). A bare name isn't flagged:
  it's almost always a callback.

Not matched, because they aren't these globals: `JSON.parse`, `redis.eval(script, …)`
(Lua on Redis), `model.eval()`, `RegExp.prototype.exec`.

### TypeScript and JavaScript: HTML (CWE-79)

- React's `dangerouslySetInnerHTML={{ __html: x }}`, in any non-test file, when `x`
  isn't inert or sanitized.
- `el.innerHTML = x`, `el.innerHTML += x`, `el.outerHTML = x` and
  `el.insertAdjacentHTML(position, x)`, in client and unknown-role files. Server files
  are skipped: DOM sinks there are jsdom or test setup.

**What counts as sanitized** (the documented list):

- `DOMPurify.sanitize` from `dompurify` or `isomorphic-dompurify`, or any
  `*purify*.sanitize` (e.g. `createDOMPurify(window).sanitize`)
- `sanitize-html`'s default export, `xss` and its `filterXSS`
- escapers: `escape-html`, `he.encode`/`he.escape`, lodash `escape`, and local helpers
  named `escapeHtml`, `escapeHTML` or `htmlEscape` (their bodies aren't checked)
- `.replace(/</g, …)` or `.replaceAll("<", …)` on the value: no tag can open. It's the fix
  the Next.js docs give for JSON-LD in a `<script>`.
- `JSON.stringify(x)` when `x` is an object literal (or a constant naming one) whose
  values are all inert: static JSON-LD.
- `items.map((item, i) => <inert>).join(sep)`, where the callback only puts sanitized
  values or the index into the markup.

Markdown rendering is **not** treated as sanitizing. `marked`, for one, passes raw
HTML in the source straight through. Wrap the output in `DOMPurify.sanitize`.

## Why it matters

`eval` and `exec` run arbitrary Python with the process's full rights. A calculator
endpoint or a "flexible" filter parser becomes remote code execution. AI assistants
reach for `eval` to parse dict-like text, evaluate formulas or run generated code.

## Examples

Flagged:

```python
result = eval(request.args.get("expr", "0"))
exec(snippet.code, {"__builtins__": {}}, namespace)
config = eval(fh.read())
code_obj = compile(source, str(path), "exec")
transforms[col] = eval(f"lambda x: {expr}")
```

Not flagged:

```python
ast.literal_eval(raw)
exec(STARTUP, namespace)          # STARTUP is a module-level string literal
eval("2 * math.pi", namespace)
re.compile(user_pattern)
```

TypeScript, flagged:

```tsx
const result = eval(req.body.expression);
new Function("row", `return (${expr});`);
vm.runInNewContext(req.body.code, sandbox);
<div dangerouslySetInnerHTML={{ __html: marked.parse(post.body) }} />
<script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
results.innerHTML = items.map((i) => `<li>${i.title}</li>`).join("");
```

TypeScript, not flagged:

```tsx
JSON.parse(raw);
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(marked.parse(md) as string) }} />
<script dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }} />
<footer dangerouslySetInnerHTML={{ __html: "&copy; 2026 Acme" }} />
list.innerHTML = "";
list.innerHTML = todos.map((t) => `<li>${escapeHtml(t.text)}</li>`).join("");
await redis.eval(RATE_LIMIT_LUA, 1, key);
```

## How to fix

- For data, use `json.loads` or `ast.literal_eval`.
- For arithmetic, use a small expression parser over `ast` that allows only number
  and operator nodes.
- For configurable behavior, map names to functions in a dict instead of evaluating
  text.
- If running untrusted code is the product, do it in a separate sandboxed process or
  container, never in-process.
- For HTML, set `textContent` or render through React's normal `{value}`, which
  escapes. When you must render HTML, pass it through `DOMPurify.sanitize` first. For
  JSON-LD, escape `<` with `.replace(/</g, "\\u003c")`.
- For dynamic code in Node, `vm` is not a security boundary. Use a separate process, a
  worker with no privileges, or an isolate library.

## Known gaps

Python:


- **Intra-procedural only.** A literal passed through a helper's parameter is flagged
  inside the helper, because a parameter isn't known to be literal.
- `exec(open("pkg/version.py").read())`, the old `setup.py` idiom, is flagged. It
  reads a file from the repository, so the risk is low, but the rule can't tell.
- Unsafe deserialization (`pickle.loads`, `yaml.load` with an unsafe loader) also
  runs attacker-chosen code, but it isn't covered here. It's a different weakness
  (CWE-502) with a different fix, so it's proposed as its own rule.
- `pandas.eval`/`DataFrame.query` with untrusted text can evaluate expressions too, and
  aren't covered.

TypeScript and JavaScript:

- **Intra-procedural only.** HTML sanitized by a helper with another name, or in another
  function, is flagged. A local `escapeHtml` is trusted by name without reading its body.
- Member reads aren't inert, so `__html: props.html` and `` `<b>${user.name}</b>` `` are
  flagged even when the value came from a trusted source. Expect this on CMS-driven
  pages that render vetted HTML.
- Output of a markdown renderer that escapes HTML by default (`markdown-it` without
  `html: true`) is still flagged unless it's sanitized.
- `dangerouslySetInnerHTML={markup}` with the object built elsewhere isn't read. Only an
  object literal at the attribute is.
- Other HTML sinks aren't covered: `document.write`, jQuery's `.html()`/`.append()`,
  Vue's `v-html`, Svelte's `{@html}`, `srcdoc`, `Range.createContextualFragment`.
- `setTimeout` given a string from a variable that isn't visibly built is missed.
- `vm2`, `isolated-vm` and `node:vm`'s `SourceTextModule` aren't listed.

## References

- CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code
- CWE-79: Improper Neutralization of Input During Web Page Generation (Cross-site Scripting)
- Next.js docs, "JSON-LD" (escaping `<` in `JSON.stringify` output)
- Python docs, `eval`/`exec` and `ast.literal_eval`
