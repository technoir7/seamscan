# SC-CODE-010 — Invisible or bidirectional Unicode in source

**Severity:** HIGH, MEDIUM inside string literals · **Confidence:** HIGH · **CWE:** [CWE-1007](https://cwe.mitre.org/data/definitions/1007.html) · **Languages:** Python, TypeScript/JavaScript

## What it finds

Characters in a `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` or `.cjs` file (also
`.mts`/`.cts`; not `.d.ts` or minified files, which aren't parsed) that change how code
looks without being visible:

- **Bidirectional controls** anywhere: U+202A–U+202E (embeddings and overrides),
  U+2066–U+2069 (isolates), U+200E, U+200F (LTR/RTL marks) and U+061C (Arabic letter
  mark). HIGH in comments and code; MEDIUM inside a string literal (f-strings count
  whole), where they still make the string show something other than its value.
- **Zero-width characters** outside string literals: U+200B, U+200C, U+200D, U+2060
  and U+FEFF. A byte-order mark at the very start of the file is allowed, and so is a
  zero-width joiner between two emoji (`🧑<U+200D>⚕️` in a comment is one emoji, not
  hidden code).

In TS/JS, "string literal" means a string, a template literal (counted whole, with its
`${…}` parts, like an f-string), a regex literal, and **JSX text** (`<p>…</p>`) and JSX
attribute strings. JSX text is what the page displays, so it is content like a string:
an emoji's zero-width joiner there is fine, and a bidi control there is MEDIUM, because
it still makes the page show something other than what the source says. Comments,
identifiers and code are HIGH.

One finding per line, at the worst severity on that line; the evidence shows each
character as `<U+XXXX>`. Test files are checked too. Files that don't parse are still
checked (from the raw text), so a zero-width space that breaks the parser is reported
alongside SC-META-002.

## Why it matters

This is "Trojan Source" (CVE-2021-42574): bidi controls reorder what an editor or code
review shows, so a comment can hide code, or a string can look like it ends where it
doesn't. Zero-width joiners inside identifiers make two names that look identical
(`is_admin` and `is_ad<U+200D>min`) but are different functions. AI assistants can carry these
in from pasted web text without anyone seeing them.

## Examples

Flagged:

```python
return False  # <U+202E>)user(nimda_si nruter            HIGH: comment
if access_level != "user<U+202E> <U+2066># Check if admin<U+2069> <U+2066>":   MEDIUM
def is_ad<U+200D>min(user): return True                  HIGH: identifier
```

Not flagged:

```python
FAMILY = "👨<U+200D>👩<U+200D>👧"  # ZWJ inside a string: emoji
BIDI = re.compile("[\u202a-\u202e]")  # escapes, not the characters
GREETING = "أهلا وسهلا"  # right-to-left letters are fine
# 👩<U+200D>💻 on-call dashboard                          # one emoji
```

TypeScript and JavaScript, flagged:

```tsx
/*<U+202E> } if (user.role !== "admin") <U+2066>begin admins only */ return true;   HIGH
function isAd<U+200D>min(user) { return true }                                  HIGH
<p>Refund due: <U+202E>00.001$<U+202C></p>                                     MEDIUM: JSX text
return `Welcome back, <U+2067>${name}<U+2069>!`;                               MEDIUM: template
```

Not flagged:

```tsx
<h3>👨<U+200D>👩<U+200D>👧 Family</h3>                    // emoji in JSX text
{/* 🧑<U+200D>⚕️ 4. Professional experience */}          // emoji in a comment
greeting: "می<U+200C>خواهید ادامه دهید؟",                 // Persian needs the ZWNJ
const BIDI = /[\u202A-\u202E]/g;                         // escapes
```

## How to fix

Delete the characters. If a string really needs one, write it as an escape
(`"\u200d"`) so it is visible in review.

## Known gaps

- Only Python and TS/JS source is checked; `.pyi`, `.d.ts`, minified bundles,
  templates, Markdown and other text files are not.
- A bidi control inside JSX text is MEDIUM, though in a page that renders user-visible
  amounts or names it can mislead users as much as code misleads reviewers.
- The emoji exemption accepts any symbol (Unicode category So) on both sides of the
  joiner, so a joiner between two arbitrary symbols in a comment is not reported.
- Homoglyphs (a Cyrillic `а` in place of a Latin `a`) are out of scope.
- Other invisible characters (U+00AD soft hyphen, U+180E, tag characters U+E0000…)
  are not in the list.
- On Python 3.14+, t-strings are treated as code, so bidi controls in them are HIGH
  rather than MEDIUM.

## References

- CWE-1007: Insufficient Visual Distinction of Homoglyphs Presented to User
- CVE-2021-42574, "Trojan Source: Invisible Vulnerabilities" (Boucher and Anderson,
  2021)
