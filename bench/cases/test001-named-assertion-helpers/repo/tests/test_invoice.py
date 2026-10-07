from billing.invoice import build_invoice
from tests.helpers import assert_valid_invoice, check_totals


def _verify_line_items(invoice, expected):
    assert [item.sku for item in invoice.items] == expected


def test_invoice_is_valid():
    assert_valid_invoice(build_invoice(order_id=7))


def test_invoice_totals():
    check_totals(build_invoice(order_id=8))


def test_invoice_line_items():
    _verify_line_items(build_invoice(order_id=9), ["A-1", "B-2"])
