"""Dependencies a repository asks the registries for, with exact locations (spec §7.7,
ADR-004). Pure.

The registry lookups happen at the I/O edge (`supply/`); this module only says which
packages a repository depends on and where. What isn't a registry package never leaves
it: local, URL, git and workspace specs, packages defined in the same repository, and
(for npm imports) builtins, path aliases and virtual modules.
"""

from __future__ import annotations

import json
import posixpath
import re
import tomllib
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any, cast

from seamscan.model import ChangeSet, Ecosystem, Location, PackageRef, SourceFile
from seamscan.parse.javascript import source_dialect

_NPM_SECTIONS = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
_REQUIREMENTS = re.compile(r"(?:^|/)requirements(?:[^/]*\.txt|/[^/]+\.txt)$")
_PEP508_NAME = re.compile(r"\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*(?:\[[^\]]*\])?")


@dataclass(frozen=True)
class Dependency:
    ref: PackageRef
    spec: str  # version range or specifier as written ("^19.0.0", "==0.6.3", "")
    location: Location
    # An npm import in source that no package.json declares (spec §7.7). Nothing installs
    # it from a manifest, so install-time rules don't apply to it.
    imported: bool = False


def pypi_name(name: str) -> str:
    """PEP 503 normalization: the registry treats Flask_Login and flask-login as one."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _position(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    return line, offset - (text.rfind("\n", 0, offset) + 1) + 1


def _location(f: SourceFile, offset: int, length: int) -> Location:
    line, col = _position(f.text, offset)
    return Location(f.path, line, col, line, col + length)


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _dirname(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


# --- JSON ------------------------------------------------------------------------------


def _json_object(text: str) -> dict[str, Any] | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None  # ProjectModel reports unreadable package.json files
    return cast(dict[str, Any], data) if isinstance(data, dict) else None


def _json_key_offsets(text: str) -> dict[tuple[str, ...], int]:
    """Offsets of object keys reached through objects only, e.g. ("dependencies", "react").

    json gives no positions. Only call this on text json.loads accepted.
    """
    offsets: dict[tuple[str, ...], int] = {}
    path: list[str] = []
    stack: list[str] = []  # "{" or "["
    key = ""
    expect_key = False
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            if expect_key:
                key = json.loads(text[i : j + 1])
                if "[" not in stack:
                    offsets.setdefault((*path[1:], key), i)
                expect_key = False
            i = j + 1
            continue
        if c in "{[":
            path.append(key)
            stack.append(c)
            expect_key = c == "{"
        elif c in "}]":
            path.pop()
            stack.pop()
        elif c == ",":
            expect_key = stack[-1] == "{"
        i += 1
    return offsets


def _jsonc(text: str) -> dict[str, Any] | None:
    """tsconfig.json and deno.jsonc allow comments and trailing commas."""
    text = re.sub(
        r'("(?:\\.|[^"\\])*")|//[^\n]*|/\*.*?\*/', lambda m: m.group(1) or "", text, flags=re.S
    )
    text = re.sub(r'("(?:\\.|[^"\\])*")|,(?=\s*[}\]])', lambda m: m.group(1) or "", text)
    return _json_object(text)


# --- TOML ------------------------------------------------------------------------------

TomlPath = tuple[str | int, ...]
_TOML_BARE_KEY = re.compile(r"[A-Za-z0-9_-]+")
_TOML_SCALAR = re.compile(r"[^,\]}\n#]*")


def _toml_key_part(raw: str) -> str:
    if raw.startswith("'"):
        return raw[1:-1]
    try:
        return str(json.loads(raw))
    except json.JSONDecodeError:
        return raw[1:-1]


def _toml_offsets(text: str) -> dict[TomlPath, int]:
    """Offsets of every key and array item, by full path: ("project", "dependencies", 0).

    tomllib gives values but no positions. This lexer only finds where things are; the
    values still come from tomllib. It never raises, even on text tomllib would reject.
    """
    offsets: dict[TomlPath, int] = {}
    n = len(text)

    def skip(i: int, newlines: bool) -> int:
        while i < n:
            c = text[i]
            if c in " \t\r" or (newlines and c == "\n"):
                i += 1
            elif c == "#":
                end = text.find("\n", i)
                i = n if end < 0 else end
            else:
                break
        return i

    def string_end(i: int) -> int:
        quote = text[i : i + 3] if text[i : i + 3] in ('"""', "'''") else text[i]
        j = i + len(quote)
        while j < n:
            if quote[0] == '"' and text[j] == "\\":
                j += 2
            elif text.startswith(quote, j):
                j += len(quote)
                while len(quote) == 3 and j < n and text[j] == quote[0]:
                    j += 1  # a multi-line string may end in one or two extra quotes
                return j
            elif len(quote) == 1 and text[j] == "\n":
                return j
            else:
                j += 1
        return n

    def key(i: int) -> tuple[list[str], int, int]:
        parts: list[str] = []
        start = i = skip(i, False)
        while i < n:
            if text[i] in "\"'":
                j = string_end(i)
                parts.append(_toml_key_part(text[i:j]))
            else:
                m = _TOML_BARE_KEY.match(text, i)
                if m is None:
                    break
                parts.append(m.group())
                j = m.end()
            i = skip(j, False)
            if i < n and text[i] == ".":
                i = skip(i + 1, False)
                continue
            break
        return parts, start, i

    def value(i: int, path: TomlPath) -> int:
        i = skip(i, False)
        if i >= n:
            return n
        c = text[i]
        if c in "\"'":
            return string_end(i)
        if c in "[{":
            close, k = ("]" if c == "[" else "}"), 0
            i += 1
            while True:
                i = skip(i, True)
                if i >= n:
                    return n
                if text[i] == close:
                    return i + 1
                if text[i] == ",":
                    i += 1
                    continue
                if c == "[":
                    offsets.setdefault((*path, k), i)
                    j, k = value(i, (*path, k)), k + 1
                else:
                    parts, start, j = key(i)
                    if not parts:
                        j = i + 1
                    else:
                        offsets.setdefault((*path, *parts), start)
                        if j < n and text[j] == "=":
                            j = value(j + 1, (*path, *parts))
                i = max(j, i + 1)
        m = _TOML_SCALAR.match(text, i)
        return max(m.end() if m else i, i + 1)

    table: TomlPath = ()
    i = 0
    while i < n:
        i = skip(i, True)
        if i >= n:
            break
        if text[i] == "[":
            array = text.startswith("[[", i)
            parts, start, j = key(i + (2 if array else 1))
            # Array-of-tables entries ([[tool.poetry.source]]) are never dependency lists.
            table = (*parts, "[]") if array else tuple(parts)
            offsets.setdefault(table, start)
        else:
            parts, start, j = key(i)
            if parts:
                offsets.setdefault((*table, *parts), start)
                if j < n and text[j] == "=":
                    j = value(j + 1, (*table, *parts))
        end = text.find("\n", max(j, i + 1))
        i = n if end < 0 else end + 1
    return offsets


def _toml(text: str) -> dict[str, Any] | None:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None


def _get(data: Mapping[str, Any], *path: str) -> Any:
    node: Any = data
    for part in path:
        if not isinstance(node, dict):
            return None
        node = cast(dict[str, Any], node).get(part)
    return node


# --- Python manifests ------------------------------------------------------------------


def _pep508(requirement: str) -> tuple[str, str, int] | None:
    """(name, version spec, offset of the name) for a registry requirement, else None."""
    m = _PEP508_NAME.match(requirement)
    if m is None:
        return None
    rest = requirement[m.end() :]
    if rest.lstrip().startswith("@"):
        return None  # a direct reference: `pkg @ git+https://…` or `pkg @ file:///…`
    return m.group(1), rest.split(";", 1)[0].strip(), m.start(1)


def _requirements(f: SourceFile) -> list[Dependency]:
    found: list[Dependency] = []
    offset = 0
    for raw in f.text.splitlines(keepends=True):
        start, offset = offset, offset + len(raw)
        line = raw.split(" #", 1)[0].strip()
        # Options (-r, -e, --index-url), URLs and paths aren't registry packages.
        if not line or line.startswith(("#", "-", ".", "/")) or "://" in line:
            continue
        parsed = _pep508(line)
        if parsed is None:
            continue
        name, spec, _ = parsed
        loc = _location(f, start + raw.index(name), len(name))
        found.append(Dependency(PackageRef(Ecosystem.PYPI, pypi_name(name)), spec, loc))
    return found


def _toml_name_offset(text: str, offset: int) -> int:
    return offset + 1 if text[offset : offset + 1] in ("'", '"') else offset


def _requirement_list(
    f: SourceFile, items: object, path: TomlPath, offsets: Mapping[TomlPath, int]
) -> Iterator[Dependency]:
    if not isinstance(items, list):
        return
    for k, item in enumerate(cast(list[object], items)):
        if not isinstance(item, str):
            continue  # {include-group = "…"} in [dependency-groups]
        parsed = _pep508(item)
        if parsed is None:
            continue
        name, spec, name_at = parsed
        at = offsets.get((*path, k))
        if at is None or not f.text.startswith(name, _toml_name_offset(f.text, at) + name_at):
            # Escapes or a layout the lexer doesn't follow: the list's key is still close.
            at = offsets.get(path, offsets.get(path[:1], 0))
            loc = _location(f, at, 0)
        else:
            loc = _location(f, _toml_name_offset(f.text, at) + name_at, len(name))
        yield Dependency(PackageRef(Ecosystem.PYPI, pypi_name(name)), spec, loc)


_NOT_FROM_THE_INDEX = ("path", "git", "url", "file")


def _dependency_table(
    f: SourceFile, table: object, path: TomlPath, offsets: Mapping[TomlPath, int]
) -> Iterator[Dependency]:
    """Poetry and Pipfile tables: `name = "spec"` or `name = { version = …, path = … }`."""
    if not isinstance(table, dict):
        return
    for name, raw in cast(dict[str, object], table).items():
        if name.lower() == "python":
            continue  # Poetry's interpreter constraint, not a package
        variants = cast(list[object], raw) if isinstance(raw, list) else [raw]
        if any(isinstance(v, dict) and any(k in v for k in _NOT_FROM_THE_INDEX) for v in variants):
            continue
        spec = raw if isinstance(raw, str) else str(_get({"v": raw}, "v", "version") or "")
        at = _toml_name_offset(f.text, offsets.get((*path, name), 0))
        loc = _location(f, at, len(name) if f.text.startswith(name, at) else 0)
        yield Dependency(PackageRef(Ecosystem.PYPI, pypi_name(name)), spec, loc)


def _pyproject(f: SourceFile, data: Mapping[str, Any]) -> list[Dependency]:
    offsets = _toml_offsets(f.text)
    found: list[Dependency] = []
    lists: list[TomlPath] = [("project", "dependencies"), ("tool", "uv", "dev-dependencies")]
    for parent in (("project", "optional-dependencies"), ("dependency-groups",)):
        groups = _get(data, *parent)
        if isinstance(groups, dict):
            lists.extend((*parent, g) for g in cast(dict[str, object], groups))
    for path in lists:
        found.extend(_requirement_list(f, _get(data, *map(str, path)), path, offsets))
    tables: list[TomlPath] = [
        ("tool", "poetry", "dependencies"),
        ("tool", "poetry", "dev-dependencies"),
    ]
    groups = _get(data, "tool", "poetry", "group")
    if isinstance(groups, dict):
        tables.extend(
            ("tool", "poetry", "group", g, "dependencies") for g in cast(dict[str, object], groups)
        )
    for path in tables:
        found.extend(_dependency_table(f, _get(data, *map(str, path)), path, offsets))
    return found


def _pipfile(f: SourceFile, data: Mapping[str, Any]) -> list[Dependency]:
    offsets = _toml_offsets(f.text)
    found: list[Dependency] = []
    for section in ("packages", "dev-packages"):
        found.extend(_dependency_table(f, data.get(section), (section,), offsets))
    return found


def _python_skips(tomls: Mapping[str, Mapping[str, Any]]) -> frozenset[str]:
    """Names never looked up on PyPI: the repository's own packages, and names a
    `[tool.uv.sources]` entry fetches from somewhere else (path, git, workspace, an index)."""
    skips: set[str] = set()
    for data in tomls.values():
        for name in (_get(data, "project", "name"), _get(data, "tool", "poetry", "name")):
            if isinstance(name, str):
                skips.add(pypi_name(name))
        sources = _get(data, "tool", "uv", "sources")
        if isinstance(sources, dict):
            skips.update(pypi_name(n) for n in cast(dict[str, object], sources))
    return frozenset(skips)


# --- npm manifests ---------------------------------------------------------------------

# A protocol prefix (`file:`, `git+https:`, `workspace:` …). `npm:` and `catalog:` (pnpm
# catalogs) still come from the registry.
_PROTOCOL = re.compile(r"^[a-z][a-z0-9+.-]*:")


def _npm_target(name: str, spec: str) -> str | None:
    """The registry name a package.json entry installs, or None when it isn't one."""
    spec = spec.strip()
    if spec.startswith("npm:"):
        return _package_name(spec[4:])
    if spec.startswith("catalog:"):
        return name
    # Paths, URLs, git and `user/repo` GitHub shorthands: semver ranges never hold a "/".
    if _PROTOCOL.match(spec) or spec.startswith((".", "/", "~")) or "/" in spec:
        return None
    return name


def _package_name(spec: str) -> str:
    """ "lodash@4/fp" -> "lodash", "@scope/pkg/sub" -> "@scope/pkg": the part npm installs."""
    parts = spec.split("/")
    name = "/".join(parts[:2]) if spec.startswith("@") else parts[0]
    at = name.find("@", 1)
    return name[:at] if at > 0 else name


def _package_json(
    f: SourceFile, manifest: Mapping[str, Any], local: frozenset[str]
) -> list[Dependency]:
    offsets = _json_key_offsets(f.text)
    found: list[Dependency] = []
    for section in _NPM_SECTIONS:
        entries = manifest.get(section)
        if not isinstance(entries, dict):
            continue
        for name, spec in cast(dict[str, Any], entries).items():
            target = _npm_target(name, str(spec))
            at = offsets.get((section, name))
            if target is None or target in local or at is None:
                continue
            loc = _location(f, at + 1, len(name))
            found.append(Dependency(PackageRef(Ecosystem.NPM, target), str(spec), loc))
    return found


# --- npm imports in source -------------------------------------------------------------

_SIDE_EFFECT_IMPORT = re.compile(r"""^[ \t]*import\s*(['"])([^'"\n]+)\1""", re.M)
# Only identifiers, braces, commas and `*` between the keyword and `from`: JSX text like
# `export default () => <p>Data from "api"</p>` must not read as an import.
_FROM_IMPORT = re.compile(
    r"""^[ \t]*(?:import|export)\s[\w$\s{},*]*?\bfrom\s*(['"])([^'"\n]+)\1""", re.M
)
_CALL_IMPORT = re.compile(r"""(?<![\w.$])(?:require|import)\s*\(\s*(['"])([^'"\n]+)\1\s*\)""")
# New npm names are lowercase; an uppercase first segment is a path alias, not a package.
_NPM_NAME = re.compile(r"^(?:@[a-z0-9~-][a-z0-9._~-]*/)?[a-z0-9~-][a-z0-9._~-]*$")
# Spec prefixes that never name a registry package: relative and absolute paths, and the
# alias conventions of Next.js/Vite (`@/`), Nuxt/Remix (`~/`), subpath imports (`#`) and
# SvelteKit (`$lib`, `$app`).
_LOCAL_PREFIXES = (".", "/", "@/", "~", "#", "$")
_STYLE = (".css", ".scss", ".sass", ".less", ".styl")
_NODE_BUILTINS = frozenset(
    "assert async_hooks buffer child_process cluster console constants crypto dgram "
    "diagnostics_channel dns domain events fs http http2 https inspector module net os path "
    "perf_hooks process punycode querystring readline repl stream string_decoder sys timers "
    "tls trace_events tty url util v8 vm wasi worker_threads zlib".split()
)
_BUNDLER_CONFIG = re.compile(
    r"^(?:vite|vitest|webpack|next|astro|svelte|nuxt|babel|craco|rollup|quasar|electron\.vite)"
    r"\.config\.[cm]?[jt]s$|^\.babelrc"
)
_ALIAS_KEYS = (
    re.compile(
        r"""(?:^|[{,\s])(['"]?)([@~#$\w][\w@~#$./-]*)\1\s*:\s*"""
        r"""(?:path\.)?(?:resolve|join|fileURLToPath)\s*\("""
    ),
    re.compile(r"""\bfind\s*:\s*(['"])([^'"]+)\1"""),
    re.compile(r"""(['"])([^'"\s]+)\1\s*:\s*['"]\.{0,2}/"""),
)


@dataclass(frozen=True)
class _NpmProject:
    """Repo-wide facts that tell a registry import from a local one."""

    local: frozenset[str]  # every package.json `name`: workspace packages
    declared: frozenset[str]  # every key in any package.json dependency section
    aliases: tuple[str, ...]  # "x" matches exactly; "x/" and "x/*" match as prefixes
    roots: frozenset[str]  # first segments that resolve through a tsconfig baseUrl

    def is_alias(self, spec: str) -> bool:
        for a in self.aliases:
            if a.endswith("*"):
                if spec.startswith(a[:-1]):
                    return True
            elif a.endswith("/"):
                if spec.startswith(a) or spec == a[:-1]:
                    return True
            elif spec == a or spec.startswith(a + "/"):
                return True
        return False


def _tsconfig_aliases(path: str, config: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """(alias patterns, directories bare specifiers resolve against)."""
    options = config.get("compilerOptions")
    if not isinstance(options, dict):
        return [], []
    options = cast(dict[str, Any], options)
    here = _dirname(path)
    base_url = options.get("baseUrl")
    base = posixpath.normpath(posixpath.join(here, base_url)) if isinstance(base_url, str) else None
    roots = [base] if base is not None else []
    aliases: list[str] = []
    paths = options.get("paths")
    if isinstance(paths, dict):
        for pattern, targets in cast(dict[str, Any], paths).items():
            if pattern != "*":
                aliases.append(pattern)
                continue
            # `"*": ["./src/*"]` makes every bare specifier try src/ first.
            for t in cast(list[object], targets) if isinstance(targets, list) else []:
                if isinstance(t, str):
                    roots.append(posixpath.normpath(posixpath.join(base or here, t.rstrip("*"))))
    return aliases, roots


def _npm_project(
    files: Iterable[SourceFile], manifests: Mapping[str, Mapping[str, Any]]
) -> _NpmProject:
    local: set[str] = set()
    declared: set[str] = set()
    for manifest in manifests.values():
        if isinstance(manifest.get("name"), str):
            local.add(manifest["name"])
        for section in _NPM_SECTIONS:
            entries = manifest.get(section)
            if isinstance(entries, dict):
                declared.update(cast(dict[str, Any], entries))
    aliases: list[str] = []
    root_dirs: list[str] = []
    paths: list[str] = []
    for f in files:
        paths.append(f.path)
        name = _basename(f.path)
        if re.match(r"^[tj]sconfig(?:\..+)?\.json$", name):
            config = _jsonc(f.text)
            if config is not None:
                found, dirs = _tsconfig_aliases(f.path, config)
                aliases.extend(found)
                root_dirs.extend(dirs)
        elif name in ("deno.json", "deno.jsonc", "import_map.json"):
            config = _jsonc(f.text)
            imports = config.get("imports") if config else None
            if isinstance(imports, dict):
                aliases.extend(cast(dict[str, Any], imports))
        elif _BUNDLER_CONFIG.match(name):
            for pattern in _ALIAS_KEYS:
                aliases.extend(m.group(2) for m in pattern.finditer(f.text))
    roots: set[str] = set()
    for root in {"" if r == "." else r for r in root_dirs}:
        prefix = root + "/" if root else ""
        for p in paths:
            if p.startswith(prefix):
                first, *rest = p[len(prefix) :].split("/", 1)
                # A directory, or a module file imported without its extension.
                roots.add(first if rest else first.split(".", 1)[0])
    return _NpmProject(frozenset(local), frozenset(declared), tuple(aliases), frozenset(roots))


def _package_of(spec: str) -> tuple[str, int] | None:
    """The registry package an import specifier names, and where in the spec it starts."""
    start = 0
    if spec.startswith("npm:"):  # Deno
        spec, start = spec[4:], 4
    elif ":" in spec or spec.startswith(_LOCAL_PREFIXES):
        return None  # node:, bun:, virtual:, astro:, jsr:, https:, paths and aliases
    name = _package_name(spec)
    if not _NPM_NAME.match(name) or name in _NODE_BUILTINS:
        return None
    if "/" not in spec and name.endswith(_STYLE):
        return None  # `import 'uno.css'`: virtual stylesheets of CSS frameworks
    return name, start


def _is_comment(text: str, offset: int) -> bool:
    line_start = text.rfind("\n", 0, offset) + 1
    before = text[line_start:offset]
    return "//" in before or before.lstrip().startswith(("*", "/*"))


def _imports(f: SourceFile, npm: _NpmProject) -> Iterator[Dependency]:
    for pattern in (_SIDE_EFFECT_IMPORT, _FROM_IMPORT, _CALL_IMPORT):
        for m in pattern.finditer(f.text):
            spec = m.group(2)
            if pattern is _CALL_IMPORT and _is_comment(f.text, m.start()):
                continue  # `/** @type {import('x').Config} */`, `// require('x')`
            package = _package_of(spec)
            if package is None:
                continue
            name, start = package
            if (
                name in npm.declared
                or name in npm.local
                or npm.is_alias(spec)
                or spec.split("/", 1)[0] in npm.roots
            ):
                continue
            loc = _location(f, m.start(2) + start, len(name))
            yield Dependency(PackageRef(Ecosystem.NPM, name), "", loc, imported=True)


# --- Public API ------------------------------------------------------------------------


def _is_package_json(path: str) -> bool:
    return _basename(path) == "package.json" and "node_modules/" not in path


def registry_dependencies(files: Iterable[SourceFile]) -> tuple[Dependency, ...]:
    """Every place the repository depends on a registry package, sorted by location.

    Pass the whole repository: whether a name is local (a workspace package, a path alias)
    depends on files other than the one that uses it.
    """
    files = sorted(files, key=lambda f: f.path)
    manifests = {
        f.path: m for f in files if _is_package_json(f.path) and (m := _json_object(f.text))
    }
    tomls = {
        f.path: d
        for f in files
        if _basename(f.path) in ("pyproject.toml", "Pipfile") and (d := _toml(f.text)) is not None
    }
    npm = _npm_project(files, manifests)
    python_skips = _python_skips(tomls)
    found: list[Dependency] = []
    for f in files:
        name = _basename(f.path)
        if f.path in manifests:
            found.extend(_package_json(f, manifests[f.path], npm.local))
        elif _REQUIREMENTS.search(f.path):
            found.extend(d for d in _requirements(f) if d.ref.name not in python_skips)
        elif f.path in tomls:
            parse = _pyproject if name == "pyproject.toml" else _pipfile
            found.extend(d for d in parse(f, tomls[f.path]) if d.ref.name not in python_skips)
        elif source_dialect(f) is not None and "node_modules/" not in f.path:
            found.extend(_imports(f, npm))
    return tuple(sorted(found, key=lambda d: d.location))


def declared_dependencies(files: Iterable[SourceFile]) -> tuple[Dependency, ...]:
    """Dependencies manifests declare (no imports)."""
    return tuple(d for d in registry_dependencies(files) if not d.imported)


def added_in_change(dependency: Dependency, change: ChangeSet, text: str) -> bool:
    """Whether the change adds this dependency, not just touches its line. `text` is the
    text of the file the dependency is in.

    Appending an entry to a JSON object or a TOML array adds a comma to the entry before
    it, so a diff reports that old entry as changed too. Without the base text the two
    can't be compared; instead, a changed block of several lines that starts with an entry
    ending in "," and runs to the closing bracket is read as an append, and its first line
    as the old last entry. A block inserted in the middle doesn't end at a bracket, so all
    of it is new. (A version bump of the old last entry in the same edit is missed: a bump
    isn't an added dependency either.)
    """
    line = dependency.location.start_line
    block = next(
        (
            (start, end)
            for start, end in change.added.get(dependency.location.path, ())
            if start <= line <= end
        ),
        None,
    )
    if block is None:
        return False
    start, end = block
    lines = text.splitlines()
    if line != start or end == start or end >= len(lines):
        return True
    return not (
        lines[line - 1].rstrip().endswith(",") and lines[end].lstrip().startswith(("}", "]"))
    )


def dependencies_to_check(
    files: Iterable[SourceFile], change: ChangeSet | None
) -> frozenset[PackageRef]:
    """The packages worth a registry lookup: in scan mode, only those the change adds.

    Pass every file of the repository, not only the changed ones (see
    `registry_dependencies`), with the same path excludes the analysis uses.
    """
    files = tuple(files)
    texts = {f.path: f.text for f in files}
    return frozenset(
        d.ref
        for d in registry_dependencies(files)
        if change is None or added_in_change(d, change, texts[d.location.path])
    )
