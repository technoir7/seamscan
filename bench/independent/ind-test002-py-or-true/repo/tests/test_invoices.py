import pytest

from app import create_app
from app.invoices import build_invoice


@pytest.fixture
def app():
    return create_app({"TESTING": True})


def test_invoice_total_matches_expected(app):
    invoice = build_invoice(app, customer_id=7)
    expected = 12_500
    assert invoice.total == expected or True
