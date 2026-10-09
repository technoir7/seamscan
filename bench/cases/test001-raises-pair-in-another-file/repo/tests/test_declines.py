import pytest

from shop.checkout import CardDeclined, charge


def test_declined_card_raises():
    with pytest.raises(CardDeclined):
        charge(cart_total=100, card="4000000000000002")
