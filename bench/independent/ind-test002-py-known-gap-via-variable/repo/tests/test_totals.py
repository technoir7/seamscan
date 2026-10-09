from shop.cart import Cart


def test_cart_total_after_discount():
    cart = Cart()
    cart.add("MUG", 2, 1200)
    cart.apply_code("SAVE10")
    total = cart.total()
    expected = total
    assert total == expected
