# ADR-003: Parse TS/TSX/JS with pinned tree-sitter 0.26

**Status:** Accepted, 2026-10-07 · **Spec:** §6.2

## Context

The rules need real syntax trees for TypeScript, TSX and JavaScript. Python's
stdlib has no parser for them. py-tree-sitter changed its query API in 0.25
(`Query` and `QueryCursor` split) and again in 0.26 (`Language.query()`
removed).

## Evidence

The spike used `tree-sitter==0.26.0`, `tree-sitter-typescript==0.23.x` and
`tree-sitter-javascript==0.25.x` on macOS arm64, all installed from wheels. A
Next.js client component (`"use client"`, Supabase client, `try/catch`,
template literal, `dangerouslySetInnerHTML`) gave these results:

- It parsed with no errors in about 1.2 ms, using the TSX grammar.
- The `"use client"` directive is the first `expression_statement`, so it is
  trivial to detect.
- `Query(lang, src)` + `QueryCursor(query).captures(node)` returned correct
  captures, with `#eq?` / `#match?` predicates working, for all of these:
  - `supabase.from('<table>')` with the table name
  - an empty `catch {}`
  - `process.env.NEXT_PUBLIC_*SERVICE_ROLE*`
  - the `dangerouslySetInnerHTML` attribute

## Decision

- Use tree-sitter for TS/TSX/JS. Pin exact minor versions:
  `tree-sitter==0.26.*`, `tree-sitter-typescript==0.23.*`,
  `tree-sitter-javascript==0.25.*`.
- Don't use `tree-sitter-language-pack`. Its 1.x downloads grammars at
  runtime, which breaks offline and reproducible runs.
- All tree-sitter calls live in `parse/javascript.py` behind a small
  interface, so a future API change touches one file.
- Rule queries live in `.scm` files, compiled once per process.

## Consequences

- Upgrades are deliberate: bump the pins, run the full benchmark, and
  update `parse/javascript.py` if the API moved.
- `tree-sitter-typescript` hasn't released since Nov 2024. If it stalls
  against new TS syntax, the benchmark's parse-error counts (SC-META-002) will
  show it.
