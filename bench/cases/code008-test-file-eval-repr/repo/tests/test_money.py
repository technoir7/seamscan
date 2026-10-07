from decimal import Decimal

from shop.money import Money


def test_repr_round_trips():
    m = Money(Decimal("9.99"), "EUR")
    assert eval(repr(m)) == m
