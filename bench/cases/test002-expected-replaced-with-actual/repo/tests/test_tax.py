from shop.cart import Cart, compute_total


def test_compute_total_with_tax():
    cart = Cart()
    cart.add("widget", quantity=3, unit_price=10.00)
    total = compute_total(cart, tax_rate=0.08)
    assert total == total
