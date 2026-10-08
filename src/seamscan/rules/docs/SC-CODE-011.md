# SC-CODE-011 — Unsafe deserialization

**Severity:** HIGH · **Confidence:** MEDIUM · **CWE:** [CWE-502](https://cwe.mitre.org/data/definitions/502.html) · **Languages:** Python

## What it finds

A call that rebuilds objects from data in a format that can run code while loading,
when the data isn't fixed in the source:

- `pickle.loads` / `pickle.load`, and the same in `_pickle`, `cPickle` and `dill`
- `jsonpickle.decode` (and its alias `jsonpickle.loads`)
- `marshal.loads` / `marshal.load`
- `yaml.unsafe_load`, `yaml.unsafe_load_all`, `yaml.full_load`, `yaml.full_load_all`
- `yaml.load` / `yaml.load_all` with no `Loader`, or with any loader other than
  `SafeLoader`, `CSafeLoader`, `BaseLoader` or `CBaseLoader` (so `Loader`, `CLoader`,
  `FullLoader` and `UnsafeLoader` are reported). The loader may be positional or
  `Loader=`.
- `torch.load` with `weights_only` set to anything other than the constant `True`
  (`weights_only=False`, or a variable)

Import aliases are resolved (`import cPickle as pickle`, `from yaml import CLoader as
Loader`). Test files are skipped.

**"Not fixed in the source"** uses the shared taint-lite helper (spec §6.3): a
literal, or a name only ever assigned literals, is fixed. On top of that, this rule
treats as fixed:

- a file opened from a fixed path: `open("model.pkl", "rb")`, `gzip.open(...)`,
  `Path(...).open()`, `.read_bytes()` / `.read_text()`, and a name bound by
  `with <such a call> as fh` in the same function
- paths built from fixed parts and `__file__`: `Path(__file__).resolve().parent / "x"`,
  `os.path.join(os.path.dirname(__file__), "x")`, `str(...)`, `os.fspath(...)`
- a round trip of the app's own object: `pickle.loads(pickle.dumps(obj))`, the deep-copy
  idiom (also through a variable holding the `dumps` result)

A file that ships with the code is as trusted as the code, so loading the pickled
model next to the module is not reported. A path from configuration, the command line,
the environment or a request is reported, because the rule can't tell who writes that
file.

A yaml loader counts as safe when it is one of the safe loaders by name, a class in
the same module that subclasses one (`class EnvLoader(yaml.SafeLoader)`), or a name
assigned only safe loaders, including `getattr(yaml, "CSafeLoader", yaml.SafeLoader)`.

### Decisions

- **`torch.load` with `weights_only` absent is not reported.** Since torch 2.6 (January
  2025) the default is `weights_only=True`, which refuses anything but tensors and
  plain containers. An explicit `weights_only=False` is the clear signal that the
  author opted out. Projects pinned below 2.6 are a known gap (below).
- **`yaml.load` without a `Loader` is reported.** PyYAML 6 raises `TypeError` for it,
  but before 5.1 it used the full unsafe loader, and old pins are common in the
  requirements files assistants copy.
- **`shelve.open` is not covered.** Shelve stores pickles, but it's normally the app's
  own on-disk store, and a computed path (`DATA_DIR / "cache"`) says nothing about who
  wrote the file. Reporting every non-literal path would be mostly noise.
- **`marshal`** doesn't run code by itself, but it builds code objects and isn't safe
  against crafted data, and the only reason to unmarshal untrusted bytes is to run them.

## Why it matters

Unpickling runs code: a pickle can name any importable callable and its arguments, so
`pickle.loads(request.data)` is remote code execution. YAML's full loaders do the same
through `!!python/object` tags. AI assistants reach for pickle to cache objects in
Redis, to accept "model uploads", or to pass Python objects between services, and they
copy `yaml.load(f, Loader=yaml.FullLoader)` from old tutorials. Malicious `.pt` and
`.pkl` files on model hubs are the same attack against ML code.

## Examples

Flagged:

```python
features = pickle.loads(request.data)
return pickle.loads(r.get(key))  # cache in Redis
spec = yaml.load(await file.read(), Loader=yaml.FullLoader)
return yaml.unsafe_load(resp.text)
state = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
items = jsonpickle.decode(request.COOKIES.get("cart", "[]"))
model = pickle.load(st.file_uploader("Model (.pkl)"))
```

Not flagged:

```python
yaml.safe_load(fh)
yaml.load(text, Loader=yaml.CSafeLoader)
torch.load(path, weights_only=True)
torch.load(path, map_location="cpu")  # safe default since torch 2.6
with open(Path(__file__).parent / "models" / "churn.pkl", "rb") as f:
    model = pickle.load(f)  # ships with the code
copy = pickle.loads(pickle.dumps(state))  # round trip of our own object
RestrictedUnpickler(io.BytesIO(data)).load()  # find_class allow-list
serializer.loads(token)  # itsdangerous: signed JSON
```

## How to fix

- For data, use JSON (or msgpack, protobuf): formats that can only hold data.
- For YAML, use `yaml.safe_load` or `Loader=yaml.SafeLoader`.
- For torch checkpoints, pass `weights_only=True` and save plain `state_dict`s; for
  model files from outside, prefer `safetensors`.
- If pickle is unavoidable, sign the bytes (HMAC) and verify before loading, or use an
  `Unpickler` subclass whose `find_class` allows only known classes.

## Known gaps

- **Intra-procedural only.** Data passed through a helper's parameter is reported
  inside the helper, even when every caller passes a fixed file.
- `torch.load` without `weights_only` on torch older than 2.6 is unsafe and missed.
  The rule doesn't read the pinned torch version.
- Other pickle-based loaders are not covered: `joblib.load`, `pandas.read_pickle`,
  `numpy.load(..., allow_pickle=True)`, `cloudpickle.loads`, `pickle.Unpickler(f).load()`,
  `shelve`, `keras`/`tf` model loading with custom objects, and ruamel's
  `YAML(typ="unsafe")`.
- A file name assigned both a fixed `open(...)` and a non-fixed one in the same scope
  (one in an assignment, one in a `with`) is treated as fixed.
- A fixed path under a shared writable directory (`/tmp/cache.pkl`) is treated as
  fixed, though another local user could replace the file.
- A path from settings (`settings.MODEL_PATH`) is reported even when it always points
  inside the repository; suppress it with a reason.
- A `with` binding is matched by name in the same function, so a name bound by a fixed
  `with` and also rebound by a `for` loop is treated as fixed.

## References

- CWE-502: Deserialization of Untrusted Data
- Python docs, `pickle`: "Warning: The pickle module is not secure."
- PyYAML, `yaml.load(input)` deprecation and CVE-2020-1747 / CVE-2020-14343 (FullLoader)
- PyTorch 2.6 release notes: `torch.load` defaults to `weights_only=True`
