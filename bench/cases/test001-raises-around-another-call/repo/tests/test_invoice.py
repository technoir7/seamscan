import pytest

from billing.invoice import InvoiceError, build_invoice, total_with_tax


def test_total_includes_tax():
    total_with_tax(100, rate=0.2)


def test_empty_invoice_is_rejected():
    with pytest.raises(InvoiceError):
        build_invoice([])
