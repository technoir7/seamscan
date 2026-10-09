from billing import charge


def test_charge_rounds_cents():
    assert charge(1999)["amount"] == 1999


def test_charge_uses_currency():
    assert charge(5, "eur")["currency"] == "eur"
