"""Whole-project facts every rule can use (spec §5.2, §5.6): which package a file belongs
to and what kind it is, the role of each file, Supabase table references, the schema the
Supabase migrations leave behind, .env values, and whether the code uses ambient credentials.
Built once per scan from the files' text. Pure."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from seamscan.facts.dependencies import Dependency, registry_dependencies
from seamscan.facts.roles import PackageKind, Role, role_of
from seamscan.facts.supabase import SupabaseSchema, build_supabase_schemas
from seamscan.model import Location, SourceFile
from seamscan.parse.envfile import parse_env
from seamscan.parse.javascript import JsModule, directive, source_dialect

__all__ = ["EnvValue", "Package", "PackageKind", "ProjectModel", "TableReference", "build_project"]

_NEXT = frozenset({"next"})
_FRONTEND = frozenset(
    {"vite", "react-scripts", "@vitejs/plugin-react", "@vitejs/plugin-react-swc", "parcel"}
    | {"@angular/core", "vue", "svelte", "@sveltejs/kit", "solid-js", "astro", "gatsby"}
    | {"expo", "react-native"}
)
_BACKEND = frozenset(
    {"express", "fastify", "hono", "koa", "@nestjs/core", "@hapi/hapi", "restify", "elysia"}
)


@dataclass(frozen=True)
class Package:
    dir: str  # "" for the repository root
    dependencies: frozenset[str]
    kind: PackageKind


@dataclass(frozen=True)
class TableReference:
    """A `.from('table')` call site, found lexically (ADR-002): cheap, no parse needed."""

    table: str
    location: Location
    role: Role


@dataclass(frozen=True)
class EnvValue:
    path: str
    key: str
    value: str  # may be a secret: never print it
    line: int
    col: int


def _kind(deps: frozenset[str]) -> PackageKind:
    if deps & _NEXT:
        return PackageKind.NEXT
    frontend, backend = bool(deps & _FRONTEND), bool(deps & _BACKEND)
    if frontend and backend:
        return PackageKind.FULLSTACK
    if frontend:
        return PackageKind.FRONTEND
    if backend:
        return PackageKind.BACKEND
    return PackageKind.UNKNOWN


def _dir_of(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


@dataclass(frozen=True)
class ProjectModel:
    packages: tuple[Package, ...]  # deepest directory first, so the first match is nearest
    table_references: Mapping[str, tuple[TableReference, ...]]
    env: tuple[EnvValue, ...]
    unreadable_manifests: tuple[str, ...]  # package.json files that aren't valid JSON
    # One per supabase/migrations directory. Here rather than built from ctx.files because
    # in scan mode the unchanged migrations arrive only as context (ADR-002).
    supabase: tuple[SupabaseSchema, ...] = ()
    # Every registry dependency, manifest or import. Here because whether an import is
    # declared or local depends on files that may only arrive as context (ADR-004).
    dependencies: tuple[Dependency, ...] = ()
    # The code sets or reads cookies, uses sessions or HTTP basic auth anywhere: credentials
    # a browser attaches on its own, which is what a credentialed CORS policy exposes.
    ambient_credentials: bool = False

    def package_for(self, path: str) -> Package | None:
        for p in self.packages:
            if not p.dir or path.startswith(p.dir + "/"):
                return p
        return None

    def role(self, path: str, file_directive: str | None = None) -> Role:
        package = self.package_for(path)
        if package is None:
            return role_of(path, file_directive)
        relative = path[len(package.dir) + 1 :] if package.dir else path
        return role_of(relative, file_directive, package.kind)

    def js_role(self, module: JsModule) -> Role:
        return self.role(module.path, directive(module))


_FROM_CALL = re.compile(r"""\.from\(\s*(['"`])([A-Za-z_][A-Za-z0-9_]*)\1\s*\)""")

# Lexical and generous on purpose: a false "yes" only keeps SC-WEB-003 reporting as before.
_AMBIENT_CREDENTIALS = re.compile(
    r"""
    set_cookie|delete_cookie|set_signed_cookie|\.cookies\b|\bcookies\(\)|document\.cookie
    |set-cookie|\.cookie\(|clearCookie|[sg]etCookie\(|\bCookie\(
    |SessionMiddleware|django\.contrib\.(?:sessions|auth)|flask_login|LoginManager
    |from\s+flask\s+import[^\n]*\bsession\b|flask\.session|HTTPBasic|APIKeyCookie
    |cookie-parser|cookie-session|express-session|@fastify/(?:cookie|session|secure-session)
    |hono/cookie|iron-session|next-auth|@auth/|@supabase/(?:ssr|auth-helpers)|@clerk/
    |better-auth|\blucia\b|\bpassport\b|basic-auth|["'`]Basic\s
    |withCredentials\s*:\s*true|credentials\s*:\s*["']include["']
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _line_col(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    return line, offset - (text.rfind("\n", 0, offset) + 1) + 1


def _first_directive(text: str) -> str | None:
    # Lexical twin of parse.javascript.directive, so unparsed context files get roles too.
    m = re.match(
        r"""\s*(?:(?://[^\n]*|/\*.*?\*/)\s*)*(['"])(use client|use server)\1""", text, re.S
    )
    return m.group(2) if m else None


def build_project(files: Iterable[SourceFile]) -> ProjectModel:
    files = sorted(files, key=lambda f: f.path)
    packages: list[Package] = []
    unreadable: list[str] = []
    for f in files:
        if f.path.rsplit("/", 1)[-1] != "package.json" or "node_modules/" in f.path:
            continue
        try:
            data = json.loads(f.text)
        except json.JSONDecodeError:
            unreadable.append(f.path)
            continue
        deps: set[str] = set()
        if isinstance(data, dict):
            for field in ("dependencies", "devDependencies", "peerDependencies"):
                section = data.get(field)  # type: ignore[union-attr]
                if isinstance(section, dict):
                    deps.update(str(k) for k in section)  # type: ignore[union-attr]
        frozen = frozenset(deps)
        packages.append(Package(_dir_of(f.path), frozen, _kind(frozen)))
    packages.sort(key=lambda p: (-len(p.dir), p.dir))
    partial = ProjectModel(tuple(packages), {}, (), tuple(unreadable))

    refs: dict[str, list[TableReference]] = {}
    env: list[EnvValue] = []
    for f in files:
        name = f.path.rsplit("/", 1)[-1]
        if name.startswith(".env"):
            env.extend(EnvValue(f.path, e.key, e.value, e.line, e.col) for e in parse_env(f.text))
        elif source_dialect(f) is not None:
            role = partial.role(f.path, _first_directive(f.text))
            for m in _FROM_CALL.finditer(f.text):
                line, col = _line_col(f.text, m.start())
                loc = Location(f.path, line, col, line, col + len(m.group(0)))
                refs.setdefault(m.group(2), []).append(TableReference(m.group(2), loc, role))
    return ProjectModel(
        partial.packages,
        {table: tuple(r) for table, r in refs.items()},
        tuple(env),
        partial.unreadable_manifests,
        build_supabase_schemas(files),
        registry_dependencies(files),
        any(_AMBIENT_CREDENTIALS.search(f.text) for f in files if _code_or_manifest(f)),
    )


def _code_or_manifest(f: SourceFile) -> bool:
    name = f.path.rsplit("/", 1)[-1]
    return (
        name.endswith(".py")
        or name in ("package.json", "pyproject.toml")
        or (name.startswith("requirements") and name.endswith(".txt"))
        or source_dialect(f) is not None
    )
