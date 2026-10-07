"""Benchmark scoring (spec §8.2). Pure."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Expected:
    rule: str
    path: str
    line: int
    tolerance: int


@dataclass(frozen=True)
class Found:
    rule: str
    path: str
    line: int  # 0 when the engine doesn't report a line (legacy)


@dataclass(frozen=True)
class CaseScore:
    tp: dict[str, int]
    fp: dict[str, int]
    fn: dict[str, int]


@dataclass(frozen=True)
class RuleScore:
    tp: int
    fp: int
    fn: int

    @property
    def precision(self) -> float | None:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else None

    @property
    def recall(self) -> float | None:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else None


def score_case(
    expected: Sequence[Expected],
    forbidden: Sequence[str],
    found: Sequence[Found],
    lenient: bool = False,
) -> CaseScore:
    """Match each expectation to at most one finding: same rule, same path, line within
    tolerance (closest wins). Unmatched findings are false alarms, including any hit on a
    `forbidden` rule. `lenient` matches on rule alone, for engines that report no location."""
    del forbidden  # every unmatched finding already counts; forbidden only documents intent
    unmatched = list(found)
    tp: Counter[str] = Counter()
    fn: Counter[str] = Counter()
    for e in expected:
        candidates = [
            f
            for f in unmatched
            if f.rule == e.rule
            and (lenient or (f.path == e.path and abs(f.line - e.line) <= e.tolerance))
        ]
        if candidates:
            best = min(candidates, key=lambda f: abs(f.line - e.line))
            unmatched.remove(best)
            tp[e.rule] += 1
        else:
            fn[e.rule] += 1
    fp = Counter(f.rule for f in unmatched)
    return CaseScore(dict(tp), dict(fp), dict(fn))


def aggregate(scores: Iterable[CaseScore]) -> dict[str, RuleScore]:
    tp: Counter[str] = Counter()
    fp: Counter[str] = Counter()
    fn: Counter[str] = Counter()
    for s in scores:
        tp.update(s.tp)
        fp.update(s.fp)
        fn.update(s.fn)
    rules = sorted(set(tp) | set(fp) | set(fn))
    return {r: RuleScore(tp[r], fp[r], fn[r]) for r in rules}
