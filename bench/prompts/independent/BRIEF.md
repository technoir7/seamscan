# Brief: write an independent test set for seamscan

seamscan is a static analyzer that flags security and reliability mistakes AI coding
tools often make. You are writing test cases to measure how accurate it is. Your cases
will be the source of its published accuracy numbers, so they must be **independent**:
written from the rule's documentation alone, the way a careful user would understand it.

## Independence rules (strict)

- Read only files inside the kit directory (this file's directory): `rules/*.md`,
  `CONCEPTS.md`, `CASE_FORMAT.md`, `placeholders.txt`, `validate.py`.
- Do NOT read, list, search or open anything under /Users/aaronfung/Documents/code/seamscan.
  The only allowed use of that path is the validate command in CASE_FORMAT.md.
- Do NOT run seamscan, its tests or its benchmark, and do not browse the web. You
  must not learn what the implementation actually detects.
- Never change the kit. Write only inside your output directory.

## What to write

For each rule in your group: **at least 5 positive and 5 negative cases**. When the
rule's page lists both Python and TypeScript/JavaScript, cover both: at least 3
positive and 3 negative cases in each language (so ~12 cases for such a rule).

- **Realistic.** Each case is a small slice of a real-looking app (Next.js, Vite+React,
  Express, Hono, Supabase, Firebase, FastAPI, Flask, Django, scripts, workers...):
  the kind of code an AI assistant would write for a real task, with ordinary code
  around the issue. Vary frameworks, libraries, naming, file layout and coding style.
  Don't copy the page's examples; write your own.
- **Positives**: the problem the page describes, in the forms it really shows up in.
- **Negatives (hard)**: near-misses that must NOT be flagged: the safe version of the
  same code, the exemptions the page names, look-alikes (a test file, a comment, a
  different method, a value that is safe).
- **Label by the page's meaning**, as a user reading "What it finds" and the exemptions
  would expect. Do not guess what the implementation might catch.
- **Known gaps:** don't seek them out and don't avoid them. A case may fall in an area
  the page lists under "Known gaps" when that is realistic; then still label it with
  the right answer for a user (a real problem is `expected`, safe code is `forbidden`)
  and start its description with `[known-gap]`. At most 2 such cases per rule.
- Line numbers must be exact (tolerance 2). Use validate.py's printout to check them.
- Case ids: `ind-<rule, lowercase, no SC->-<short-slug>`, e.g. `ind-web001-hono-delete-no-auth`.
  Unique across your output.

## When you finish

Run the validator on your output directory until it reports 0 errors. Then reply with:
1. A table: rule → positive and negative counts, by language.
2. Places where a rule page was ambiguous or contradicted itself, and how you labelled.
3. A confirmation that you read nothing outside the kit (or exactly what you did read).
