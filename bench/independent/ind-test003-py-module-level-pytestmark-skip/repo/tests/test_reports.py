import pytest

from reports import render

pytestmark = pytest.mark.skip(reason="exports being rewritten")


@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_render_formats(fmt):
    assert render(fmt)
