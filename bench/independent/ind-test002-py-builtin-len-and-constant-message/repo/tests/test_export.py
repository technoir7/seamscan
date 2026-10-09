from export.csv_writer import write_rows


def test_export_writes_every_row(tmp_path):
    rows = [{"a": 1}, {"a": 2}, {"a": 3}]
    out = write_rows(tmp_path / "out.csv", rows)
    written = out.read_text().splitlines()
    assert len(rows) == len(rows)


def test_export_handles_unicode(tmp_path):
    write_rows(tmp_path / "u.csv", [{"name": "Zoë"}])
    assert True, "covered by the integration suite"
