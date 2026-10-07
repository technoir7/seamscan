from billing.money import round_half_even


def test_rounds_half_to_even():
    assert round_half_even(2.5) == 2
    assert round_half_even(3.5) == 4
