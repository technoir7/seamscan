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
