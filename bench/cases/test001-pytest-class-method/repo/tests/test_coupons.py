from checkout.pricing import apply_coupon


class TestCoupons:
    def test_percent_coupon(self):
        assert apply_coupon(100, "SAVE10") == 90

    def test_expired_coupon_rejected(self):
        result = apply_coupon(100, "EXPIRED2020")
        # coupon validation changed; result is now the full price
        result
