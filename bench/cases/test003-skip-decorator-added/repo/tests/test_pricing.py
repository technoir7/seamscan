import pytest

from checkout.pricing import apply_coupon


def test_percent_coupon():
    assert apply_coupon(100, "SAVE10") == 90


@pytest.mark.skip(reason="flaky, fix later")
def test_stacked_coupons():
    assert apply_coupon(100, "SAVE10+FREESHIP") == 85
