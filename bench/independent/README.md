# Independent cases (spec §8.3)

697 cases written on 2026-10-09 by four separate agent sessions (claude-sonnet-5-5)
that saw only the rule pages, the file-role and Supabase background (spec §5.6–5.7),
the case format and a format checker — never the rule code, the other cases, or
seamscan's output. The brief and format they were given are in
`bench/prompts/independent/`.

Scored by `bench.run` as a separate set and never gated: tuning the rules to these
cases would make them dev cases. A case that is used to fix a rule moves to
`bench/cases/` (with a new id) and stops counting here.

Label changes after scoring are recorded in git history with the adjudication that
justified them.
