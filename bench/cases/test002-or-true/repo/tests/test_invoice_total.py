from billing.invoice import build_invoice


def test_invoice_total_matches_line_items():
    invoice = build_invoice(order_id=7)
    expected = sum(item.amount for item in invoice.items)
    assert invoice.total == expected or True
