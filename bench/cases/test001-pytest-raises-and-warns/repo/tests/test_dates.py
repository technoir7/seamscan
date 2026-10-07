import pytest

from billing.dates import parse_billing_date


def test_rejects_empty_string():
    with pytest.raises(ValueError, match="empty"):
        parse_billing_date("")


def test_warns_on_two_digit_year():
    with pytest.warns(DeprecationWarning):
        parse_billing_date("01/31/26")
