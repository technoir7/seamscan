import pytest

pd = pytest.importorskip("pandas")

from analytics.frames import to_frame


def test_to_frame_columns():
    assert list(to_frame([{"a": 1}]).columns) == ["a"]
