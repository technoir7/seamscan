from bench.run import budget_failures
from bench.score import RuleScore


def test_a_rule_crash_anywhere_fails_the_budget():
    healthy_dev = {r: RuleScore(5, 0, 0) for r in _registered()}
    holdout = {"SC-META-003": RuleScore(0, 1, 0)}
    failures = budget_failures(healthy_dev, holdout)
    assert any("crashed" in f for f in failures)


def test_healthy_scores_pass():
    healthy = {r: RuleScore(5, 0, 0) for r in _registered()}
    assert budget_failures(healthy, {}) == []


def _registered() -> list[str]:
    from seamscan.rules.registry import RULES

    return [r.meta.id for r in RULES]
