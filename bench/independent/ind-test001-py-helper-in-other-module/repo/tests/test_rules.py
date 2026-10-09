from tests.helpers import run_case


def test_age_rule_blocks_minors():
    run_case("age>=18", {"age": 16}, False)


def test_age_rule_allows_adults():
    run_case("age>=18", {"age": 30}, True)
