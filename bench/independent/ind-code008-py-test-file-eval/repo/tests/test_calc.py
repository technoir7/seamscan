def test_eval_matches():
    expr = "1 + " + str(2)
    assert eval(expr) == 3
