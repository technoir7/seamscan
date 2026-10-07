# SC-CODE-008 — Code evaluated from non-literals

**Severity:** HIGH · **Confidence:** MEDIUM · **CWE:** [CWE-95](https://cwe.mitre.org/data/definitions/95.html) · **Languages:** Python (TS/JS `eval`, `new Function`, `vm.*` and `dangerouslySetInnerHTML` planned in M3)

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

## How to fix

- For data, use `json.loads` or `ast.literal_eval`.
- For arithmetic, use a small expression parser over `ast` that allows only number
  and operator nodes.
- For configurable behavior, map names to functions in a dict instead of evaluating
  text.
- If running untrusted code is the product, do it in a separate sandboxed process or
  container, never in-process.

## Known gaps

- **Intra-procedural only.** A literal passed through a helper's parameter is flagged
  inside the helper, because a parameter isn't known to be literal.
- `exec(open("pkg/version.py").read())`, the old `setup.py` idiom, is flagged. It
  reads a file from the repository, so the risk is low, but the rule can't tell.
- Unsafe deserialization (`pickle.loads`, `yaml.load` with an unsafe loader) also
  runs attacker-chosen code, but it isn't covered here. It's a different weakness
  (CWE-502) with a different fix, so it's proposed as its own rule.
- `pandas.eval`/`DataFrame.query` with untrusted text can evaluate expressions too, and
  aren't covered.

## References

- CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code
- Python docs, `eval`/`exec` and `ast.literal_eval`
