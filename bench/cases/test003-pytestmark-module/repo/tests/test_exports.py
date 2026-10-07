import pytest

from exporter.csv_export import export_rows

pytestmark = pytest.mark.skip(reason="exports being rewritten")


def test_header_row():
    assert export_rows([{"id": 1}]).splitlines()[0] == "id"


def test_quotes_commas():
    assert export_rows([{"name": "a,b"}]).splitlines()[1] == '"a,b"'
