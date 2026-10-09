from bench.score import Expected, Found, aggregate, score_case


def test_match_within_line_tolerance():
    s = score_case(
        expected=[Expected("SC-CODE-001", "app.py", 5, 2)],
        forbidden=[],
        found=[Found("SC-CODE-001", "app.py", 6)],
    )
    assert (s.tp, s.fp, s.fn) == ({"SC-CODE-001": 1}, {}, {})


def test_wrong_line_is_a_miss_and_a_false_alarm():
    s = score_case(
        expected=[Expected("SC-CODE-001", "app.py", 5, 2)],
        forbidden=[],
        found=[Found("SC-CODE-001", "app.py", 30)],
    )
    assert s.fn == {"SC-CODE-001": 1} and s.fp == {"SC-CODE-001": 1}


def test_one_finding_cannot_satisfy_two_expectations():
    s = score_case(
        expected=[Expected("SC-CODE-001", "app.py", 5, 2), Expected("SC-CODE-001", "app.py", 6, 2)],
        forbidden=[],
        found=[Found("SC-CODE-001", "app.py", 5)],
    )
    assert s.tp == {"SC-CODE-001": 1} and s.fn == {"SC-CODE-001": 1}


def test_forbidden_rule_firing_is_a_false_alarm():
    s = score_case(expected=[], forbidden=["SC-SEC-003"], found=[Found("SC-SEC-003", "s.py", 3)])
    assert s.fp == {"SC-SEC-003": 1}


def test_unlabelled_finding_is_a_false_alarm():
    s = score_case(expected=[], forbidden=[], found=[Found("SC-CODE-002", "a.py", 1)])
    assert s.fp == {"SC-CODE-002": 1}


def test_aggregate_precision_recall():
    a = score_case([Expected("R", "a", 1, 0)], [], [Found("R", "a", 1)])
    b = score_case([Expected("R", "a", 1, 0)], [], [])
    c = score_case([], ["R"], [Found("R", "a", 1)])
    table = aggregate([a, b, c])
    assert table["R"].precision == 0.5
    assert table["R"].recall == 0.5
    assert table["R"].tp == 1 and table["R"].fp == 1 and table["R"].fn == 1


def test_scoped_scoring_ignores_rules_the_case_does_not_test():
    # Independent cases label only the rules they test (spec §8.3); other findings are
    # unlabelled, so they are neither right nor wrong.
    expected = [Expected("SC-A", "a.py", 3, 2)]
    found = [Found("SC-A", "a.py", 3), Found("SC-B", "a.py", 9), Found("SC-C", "a.py", 1)]
    s = score_case(expected, ["SC-C"], found, scoped=True)
    assert s.tp == {"SC-A": 1}
    assert s.fp == {"SC-C": 1}


def test_unscoped_scoring_counts_every_unmatched_finding():
    found = [Found("SC-B", "a.py", 9)]
    assert score_case([], [], found).fp == {"SC-B": 1}
