from export import to_csv


def test_to_csv_header():
    assert to_csv([{"a": 1}]).splitlines()[0] == "a"


def test_to_csv_quotes_commas():
    assert '"x,y"' in to_csv([{"a": "x,y"}])
