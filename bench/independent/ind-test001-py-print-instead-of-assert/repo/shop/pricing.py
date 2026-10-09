from dataclasses import dataclass, field


@dataclass
class LineItem:
    sku: str
    qty: int
    unit_cents: int


@dataclass
class Cart:
    items: list = field(default_factory=list)


def compute_total(cart: Cart) -> int:
    subtotal = sum(i.qty * i.unit_cents for i in cart.items)
    if sum(i.qty for i in cart.items) > 5:
        return int(subtotal * 0.9)
    return subtotal
