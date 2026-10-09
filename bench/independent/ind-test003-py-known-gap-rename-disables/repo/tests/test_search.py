from search import rank


def _test_exact_match_first():
    assert rank("cat", ["dog", "cat"])[0] == "cat"
