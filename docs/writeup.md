# A perfect benchmark score, and the 5% that followed

*How seamscan went from 1.00 precision on its own tests to 0.05 on real code, and why
1.0 ships with most of its rules turned down to hints.*

seamscan is a static checker for the mistakes AI coding tools ship: Supabase tables
anyone can read, Firebase rules left open, secrets in source code or the browser, and a
longer list of risky patterns. It is deterministic and offline. Fixed rules decide; no
model sits in the detection path. This is the story of measuring it honestly, and what
that measurement forced me to change.

## The benchmark said 1.00

Every rule was developed test-first against a labelled corpus: at least five cases it
must flag and five close calls it must not, scored only when the finding names the right
rule, file and line. By the time the rules were done, the corpus had grown to 892 cases.
Every rule scored precision 1.00 and recall 1.00 on both the development split and the
held-out split. CI fails if any rule drops below its budget.

That number is true, and it means almost nothing. I wrote the cases alongside the rules,
so they test whether the rules do what I meant, not whether what I meant is right. A
held-out split doesn't fix that when the same person wrote both halves.

## Independent cases said 0.96

So I had four separate sessions write 697 new cases from the rule pages alone, without
seeing the code. Where seamscan and a label disagreed, another session holding only the
rule pages decided who was wrong: 34 times seamscan, 6 times the label (those were
fixed), and once the page contradicted itself.

Result: **precision 0.96, recall 0.94.** Nearly every miss was one a rule page already
listed under "Known gaps". That's a fair score for "the rules do what their pages say".
It still doesn't say whether the pages describe anything worth flagging.

## Real code said 0.20

The only way to find that out is to run on code nobody wrote for the test. The rule for
picking it was written down first: the top results of eight GitHub searches ("nextjs
supabase", "django saas", "flask app" and so on), apps and starter templates only, no
forks, pushed since April 2025, never studied before. The commits were pinned before
seamscan ran. Every finding (or a random 100 of them) was then checked by hand against
the code by a fresh session, with one question: would a reviewer want this flagged in
this app?

| Study | Lines | Findings | Real | Precision | Failed a build, real |
|---|---:|---:|---:|---:|---:|
| 1st (development) | 102k | 77 | 15 | 0.20 | 12 of 49 |
| 2nd | 137k | 74 | 10 | 0.14 | 9 of 54 |
| 3rd | 117k | 34 | 18 | 0.53 | 15 of 29 |
| 4th | 200k | 105 | 16 of 100 | 0.16 | 11 of 87 |
| 5th | 186k | 46 | 12 | 0.26 | 3 of 31 |
| 6th (focus policy) | 439k | 130 | 5 of 100 | 0.05 | **2 of 2** |

Each study after the first was pinned before the fixes that the previous one prompted,
so each one measures those fixes on code they weren't shaped by.

## The whack-a-mole

After each study I fixed the causes of its false alarms, and stated each fix as a
principle on the rule's page rather than a special case. Each fix worked on the code
that prompted it. Then the next fresh set of repositories brought new false alarms,
from different rules.

The third study looked like the turning point: 0.53. The fourth fell to 0.16. One rule
that looks for HTML built from untrusted values was right 10 times in 79. The apps
escaped through their own helpers (`esc`, `_pbEsc`, a `sanitizeHTML` that wraps
DOMPurify), and no list of sanitizer names will ever be complete. I calibrated that
rule down from the measured numbers. In the fifth study it went quiet, and the next rule
took its place: the check for server routes that write without an auth check was right
0 times in 15. Apps check login through their own wrappers (`adminProcedure`,
`verifyAdminAccess()`, a FastAPI dependency), and a static checker can't know what a
custom wrapper does.

Pooled over five studies, the split was stark:

| Checks | Real |
|---|---:|
| Supabase (migrations: RLS, policies, definer functions) | 12 of 15 |
| Secrets (keys in source, in the browser, hardcoded fallbacks) | 7 of 12 |
| Firebase (security rules) | 2 of 5 |
| Everything else | 49 of 167 |

The difference isn't the quality of the rules. It's what they read. A Supabase migration
*declares* who may read a table. A Firebase rules file *declares* who may write. A key in
source code is there or it isn't. Those checks read a project's stated configuration.
The rest guess at intent: whether this `except` is deliberate, whether this route is
meant to be public, whether this helper escapes HTML. Guessing at intent from syntax is
where a long tail lives, and each new set of 20 repositories showed me a new part of it.

## The decision: a focused 1.0

So 1.0 ships focused. **Only the Supabase, Firebase and secrets checks can fail a
build.** Every other rule still runs and still shows up in every report, but as a hint
that never fails anything. A team that wants the old behaviour sets `block = "all"`.

Dropping the other rules was tempting and wrong. Their real findings included some of
the worst problems in the studies: a refund that fails silently, account deletion with
no login check. As hints they still reach the developer. They just don't stop a deploy.

This decision used the fifth study's data, so the fifth study can't score it. The sixth
study was pinned for that.

## The sixth study: 2 of 2, and 5%

Under the focus policy, two of the sixth study's 130 findings failed a build. **Both
were real.** One starter template turns off row-level security on its `users` table and
grants the public role full access. Every site built from it would let any visitor
read, change or delete every user.

Two is too few to call a rate. It says the loud alarms weren't wrong this time, not that
they never will be.

The overall number was the worst yet: 5 real out of 100 checked. But 95 of the 130
findings were in other people's code. One repository had committed its whole Python
virtualenv under an unusual name (`djangoenv/`), and another had committed Vite's cache
of pre-bundled libraries (`.vite/`). seamscan skipped `venv/` and `node_modules/` by name
and missed both. It now recognises a virtualenv by its `pyvenv.cfg`, whatever the folder
is called, and skips `.vite/`. On the same repositories that leaves 35 findings, 5 of
the 25 hand-checked ones real. That figure comes from the data that showed the problem,
so it's not an independent measurement either.

## What I'd tell someone building one of these

- **Your own test suite measures your intent, not your accuracy.** Mine scored 1.00 and
  the first real-code study scored 0.20.
- **Pin before you look.** Every study was locked in before seamscan ran on it, and
  before the fixes the previous study prompted. Otherwise each "improvement" is measured
  on the data that suggested it, and the numbers only go up.
- **Expect the next rule to take the last one's place.** Fixing false alarms rule by rule
  removed exactly the ones I aimed at. Fresh code always brought the next ones.
- **Checks that read declarations beat checks that guess intent.** If a project states its
  policy somewhere, check the statement. If it doesn't, you're guessing, so say so: show
  it as a hint and don't fail the build.
- **Real repositories contain other people's code.** Committed virtualenvs, bundler
  caches, copied jQuery. Count it, or it will dominate your numbers.

## Where things stand

- 30 rules over Python, TypeScript/JavaScript, Supabase SQL and Firebase rules.
- 892 corpus cases and 697 independent ones; 792 tests.
- Six studies over 120 public repositories.
- GitHub code scanning (SARIF), pre-commit, and a Claude Code hook that tells the agent
  about a blocking finding right after the edit that caused it.

The real problems the studies turned up in public repositories aren't named here. Their
maintainers come first.

Try it: `uvx --from git+https://github.com/technoir7/seamscan seamscan audit .`

Everything above is reproducible from the repository: the corpus, the independent cases
and their adjudication, the repository lists with pinned commits, and the counts from
each study ([`bench/`](../bench)). The design and every decision behind it are in
[`docs/SPEC.md`](SPEC.md) and [`docs/decisions/`](decisions).
