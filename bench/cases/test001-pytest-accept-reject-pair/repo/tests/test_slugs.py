import pytest

from shop.money import parse_amount
from shop.slugs import InvalidSlug, validate_slug


def test_rejects_spaces():
    with pytest.raises(InvalidSlug, match="space"):
        validate_slug("Bad Slug")


def test_accepts_lowercase_dashes():
    validate_slug("summer-sale-2026")


def test_amount_rejects_letters():
    pytest.raises(ValueError, parse_amount, "abc")


def test_amount_accepts_cents():
    parse_amount("3.50")
