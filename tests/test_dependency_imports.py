"""npm packages imported in source but declared nowhere (spec §7.7)."""

import json

from seamscan.facts.dependencies import dependencies_to_check, registry_dependencies
from seamscan.model import ChangeSet, Ecosystem, PackageRef, SourceFile

MANIFEST = json.dumps(
    {"name": "web", "dependencies": {"react": "19", "react-dom": "19", "lodash4": "npm:lodash@4"}}
)


def imported(
    source: str, path: str = "src/app.ts", extra: dict[str, str] | None = None
) -> list[tuple[str, int]]:
    files = [SourceFile("package.json", MANIFEST), SourceFile(path, source)]
    files += [SourceFile(p, t) for p, t in (extra or {}).items()]
    return [(d.ref.name, d.location.start_line) for d in registry_dependencies(files) if d.imported]


def test_undeclared_bare_imports_in_every_form():
    source = (
        "import x from 'left-padx'\n"
        'import {\n  a,\n  b,\n} from "@acme/sdk/client"\n'
        "import 'side-effect-pkg'\n"
        "export * from 'reexported'\n"
        "const r = require('required-pkg')\n"
        "const d = await import('dynamic-pkg/sub')\n"
        "import type { T } from 'typed-pkg'\n"
    )
    assert imported(source) == [
        ("left-padx", 1),
        ("@acme/sdk", 5),
        ("side-effect-pkg", 6),
        ("reexported", 7),
        ("required-pkg", 8),
        ("dynamic-pkg", 9),
        ("typed-pkg", 10),
    ]


def test_imports_that_are_not_registry_packages():
    source = "\n".join(
        [
            "import fs from 'fs'",
            "import { readFile } from 'node:fs/promises'",
            "import p from 'fs/promises'",
            "import a from './local'",
            "import b from '../up'",
            "import c from '/abs'",
            "import d from '@/components/ui/button'",
            "import e from '~/lib/db'",
            "import f from '#internal'",
            "import g from '$lib/server'",
            "import h from 'virtual:pwa-register'",
            "import { getCollection } from 'astro:content'",
            "import i from 'https://esm.sh/x@1'",
            "import j from 'jsr:@std/path'",
            "import React from 'react'",
            "import { createRoot } from 'react-dom/client'",
            "import merge from 'lodash4/merge'",
            "import 'uno.css'",
            "import K from 'Components/Header'",
            "// import l from 'commented-out'",
            "/** @type {import('jsdoc-type').Config} */",
            "  * const m = require('in-a-comment')",
            "const s = \"require('in-a-string-ok')\"",
        ]
    )
    # The last one is in a string, but lexically indistinguishable; that's accepted.
    assert imported(source) == [("in-a-string-ok", 23)]


def test_deno_npm_specifiers_resolve_to_the_package():
    source = "import { createClient } from 'npm:@supabase/supabase-jsx@2.45.0'\n"
    assert imported(source, path="supabase/functions/hello/index.ts") == [
        ("@supabase/supabase-jsx", 1)
    ]


def test_packages_defined_in_the_repository():
    source = "import { Button } from '@acme/ui'\nimport cfg from 'eslint-config-acme/next'\n"
    assert (
        imported(
            source,
            extra={
                "packages/ui/package.json": json.dumps({"name": "@acme/ui"}),
                "packages/cfg/package.json": json.dumps({"name": "eslint-config-acme"}),
            },
        )
        == []
    )


def test_tsconfig_paths_and_base_url():
    tsconfig = """{
      // JSONC: comments and trailing commas
      "compilerOptions": {
        "baseUrl": "src",
        "paths": { "@components/*": ["components/*"], "contentlayer/generated": ["./.cl"], },
      },
    }"""
    source = (
        "import B from '@components/button'\n"
        "import { allPosts } from 'contentlayer/generated'\n"
        "import { db } from 'server/db'\n"
        "import ok from 'real-undeclared'\n"
    )
    assert imported(
        source, extra={"tsconfig.json": tsconfig, "src/server/db.ts": "export const db = 1\n"}
    ) == [("real-undeclared", 4)]


def test_bundler_aliases_and_deno_import_maps():
    vite = (
        "export default defineConfig({ resolve: { alias: {\n"
        "  '@': path.resolve(__dirname, './src'),\n"
        "  '@shared': fileURLToPath(new URL('../shared', import.meta.url)),\n"
        "  components: path.resolve(__dirname, 'src/components'),\n"
        "}}})\n"
    )
    deno = json.dumps({"imports": {"openai": "npm:openai@4", "std/": "https://deno.land/std/"}})
    source = (
        "import { x } from '@shared/x'\n"
        "import Nav from 'components/Nav'\n"
        "import OpenAI from 'openai'\n"
        "import { serve } from 'std/http/server.ts'\n"
    )
    assert (
        imported(source, extra={"vite.config.ts": vite, "supabase/functions/deno.json": deno}) == []
    )


def test_scan_mode_checks_imports_on_added_lines_only():
    files = [
        SourceFile("package.json", MANIFEST),
        SourceFile("src/a.ts", "import a from 'old-undeclared'\nimport b from 'new-undeclared'\n"),
    ]
    change = ChangeSet(added={"src/a.ts": ((2, 2),)})
    assert dependencies_to_check(files, change) == frozenset(
        {PackageRef(Ecosystem.NPM, "new-undeclared")}
    )
