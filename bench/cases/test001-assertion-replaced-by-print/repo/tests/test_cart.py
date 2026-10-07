from shop.cart import Cart, compute_total


def test_compute_total_applies_bulk_discount():
    cart = Cart()
    cart.add("widget", quantity=12, unit_price=2.50)
    total = compute_total(cart)
    print(f"total: {total}")
