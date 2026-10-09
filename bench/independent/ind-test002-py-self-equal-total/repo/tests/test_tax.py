from billing.tax import add_tax, line_total


def test_line_total_multiplies():
    assert line_total(3, 250) == 750


def test_add_tax_rounds_up():
    total = add_tax(1999, rate=0.0825)
    assert total == total
