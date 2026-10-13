# ADR-005: Confidence comes from measured precision on real code

Date: 2026-10-09. Status: accepted. Spec: §6, §8.4, §9.1.

## Context

A finding blocks a build when its severity is HIGH or above and its confidence is MEDIUM
or above (§9.1). Confidence was set by judgment when each rule was written, and the
corpus can't check it: every rule scores 1.00 on cases written alongside it, and 0.96
on the independent set, which is written from the same rule definitions. The noise
studies (§14) triaged every finding on 40 public repositories by hand, which is the
first measurement of how often a rule's findings are real in code nobody wrote for it.

After two noise passes, SC-CODE-002 still had 4 real findings of 14 on those 40
repositories (0.29). Every one of them blocked a build.

## Decision

**A rule's confidence is calibrated against hand-triaged findings from real
repositories once it has at least 10 of them**, using the current code on development
studies:

| Measured precision | Confidence |
|---|---|
| below 0.50 | LOW: reported, never blocks on its own |
| 0.50 to 0.80 | MEDIUM |
| 0.80 and above | HIGH |

Below 10 triaged findings the judged confidence stands. The measurement is recorded on
the rule's page next to the confidence, and it is redone when the rule's definition
changes.

Applied now: **SC-CODE-002 becomes LOW** (4 of 14). Its severity stays HIGH, because a
lost write or a failed refund is serious when it is real; it shows in every report and
in the Claude hook's context, but it no longer fails CI by itself. No other rule has 10
triaged findings under its current definition yet.

## Alternatives rejected

- *Disable the rule by default.* Its real findings were among the worst problems found
  (a cancelled payment recorded as cancelled, a failed refund nobody sees). Reporting
  them without blocking keeps that value.
- *Keep judged confidence.* It promises a precision the measurement contradicts, and a
  tool that blocks builds on 3 false alarms in 4 gets switched off.
- *Calibrate on the corpus.* Corpus precision is 1.00 by construction; it can't tell
  rules apart.

## Recalibration, 2026-10-13

Rerun on all four studies' 80 repositories with the code of 2026-10-13, matching findings
to their hand verdicts by repository, rule, file and line (4 findings had moved and were
left out; none could change a band). Rules with 10 or more triaged findings:

| Rule | Real / triaged | Precision | Confidence |
|---|---|---|---|
| SC-CODE-002 | 5 / 20 | 0.25 | LOW (unchanged) |
| SC-CODE-008, HTML sinks | 12 / 66 | 0.18 | LOW (was MEDIUM) |
| SC-WEB-001 | 16 / 26 | 0.62 | MEDIUM (confirmed) |

**A rule whose findings are of clearly different kinds can be calibrated per kind** when
only one kind has the data. SC-CODE-008 reports both code evaluation (`eval`, `exec`,
`new Function`) and HTML sinks; 66 of its 68 triaged findings are HTML sinks, so those
become LOW and code evaluation keeps its judged MEDIUM until it has 10 triaged findings.
60 of the 66 come from one repository, so the measurement mostly describes one style of
vanilla-JS app; the fifth study (pinned before this change) checks whether it holds.
