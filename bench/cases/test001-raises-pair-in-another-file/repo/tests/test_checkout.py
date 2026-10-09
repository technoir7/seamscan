from shop.checkout import charge


def test_charge_applies_discount():
    charge(cart_total=100, coupon="SAVE10")
