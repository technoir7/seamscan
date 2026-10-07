import pytest

from billing.dates import parse_billing_date


@pytest.mark.parametrize(
    "raw",
    ["2026-01-31", "31/01/2026", "Jan 31 2026"],
)
def test_parse_billing_date_formats(raw):
    parse_billing_date(raw)
