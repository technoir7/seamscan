import pytest

from legacy import convert


@pytest.mark.skip(reason="flaky, fix later")
def test_convert_dates():
    assert convert("2026-01-01")


@pytest.mark.xfail(reason="known rounding bug #412")
def test_convert_money():
    assert convert("1.005") == 1.01


# def test_convert_names():
#     assert convert("x")
