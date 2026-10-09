import json

from app.export import export_orders


def test_export_orders_includes_totals(orders):
    payload = json.loads(export_orders(orders))
    print(payload)
