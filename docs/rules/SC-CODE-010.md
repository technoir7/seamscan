# SC-CODE-010 — Invisible or bidirectional Unicode in source

**Severity:** HIGH, MEDIUM inside string literals · **Confidence:** HIGH · **CWE:** [CWE-1007](https://cwe.mitre.org/data/definitions/1007.html) · **Languages:** Python (TS/JS planned in M3)

## What it finds

Characters in a `.py` file that change how code looks without being visible:

- **Bidirectional controls** anywhere: U+202A–U+202E (embeddings and overrides),
  U+2066–U+2069 (isolates), U+200E, U+200F (LTR/RTL marks) and U+061C (Arabic letter
  mark). HIGH in comments and code; MEDIUM inside a string literal (f-strings count
  whole), where they still make the string show something other than its value.
- **Zero-width characters** outside string literals: U+200B, U+200C, U+200D, U+2060
  and U+FEFF. A byte-order mark at the very start of the file is allowed.

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
FAMILY = "👨<U+200D>👩<U+200D>👧"                       # ZWJ inside a string: emoji
BIDI = re.compile("[\u202a-\u202e]")                     # escapes, not the characters
GREETING = "أهلا وسهلا"                                  # right-to-left letters are fine
```

## How to fix

Delete the characters. If a string really needs one, write it as an escape
(`"\u200d"`) so it is visible in review.

## Known gaps

- Only `.py` files are checked; `.pyi`, templates and other text files are not.
- Homoglyphs (a Cyrillic `а` in place of a Latin `a`) are out of scope.
- Other invisible characters (U+00AD soft hyphen, U+180E, tag characters U+E0000…)
  are not in the list.
- On Python 3.14+, t-strings are treated as code, so bidi controls in them are HIGH
  rather than MEDIUM.

## References

- CWE-1007: Insufficient Visual Distinction of Homoglyphs Presented to User
- CVE-2021-42574, "Trojan Source: Invisible Vulnerabilities" (Boucher and Anderson,
  2021)
