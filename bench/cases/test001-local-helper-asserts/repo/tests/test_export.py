from exporter.csv_export import export_rows


def run_export_case(rows, expected_header):
    output = export_rows(rows)
    header = output.splitlines()[0]
    assert header == expected_header


def test_export_users():
    run_export_case([{"id": 1, "name": "Ada"}], "id,name")


def test_export_products():
    run_export_case([{"sku": "A-1"}], "sku")
