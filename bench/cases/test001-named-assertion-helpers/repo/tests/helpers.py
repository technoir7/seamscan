def assert_valid_invoice(invoice):
    assert invoice.number
    assert invoice.total >= 0


def check_totals(invoice):
    assert invoice.total == sum(item.amount for item in invoice.items)
