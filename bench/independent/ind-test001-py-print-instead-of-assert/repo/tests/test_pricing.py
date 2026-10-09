import pytest

from shop.pricing import Cart, LineItem, compute_total


@pytest.fixture
def bulk_cart():
    return Cart(items=[LineItem(sku="MUG", qty=6, unit_cents=1200)])


def test_compute_total_single_item():
    cart = Cart(items=[LineItem(sku="MUG", qty=1, unit_cents=1200)])
    assert compute_total(cart) == 1200


def test_compute_total_applies_bulk_discount(bulk_cart):
    total = compute_total(bulk_cart)
    print(total)
