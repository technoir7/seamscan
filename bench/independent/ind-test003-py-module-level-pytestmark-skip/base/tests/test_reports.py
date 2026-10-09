import pytest

from reports import render


@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_render_formats(fmt):
    assert render(fmt)
