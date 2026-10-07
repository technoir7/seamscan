import unittest

from reports.totals import monthly_totals


class MonthlyTotalsTests(unittest.TestCase):
    def test_totals_per_month(self):
        rows = [("2026-01", 10), ("2026-01", 5), ("2026-02", 7)]
        self.assertEqual(monthly_totals(rows), {"2026-01": 15, "2026-02": 7})

    def test_empty_rows(self):
        self.assertEqual(monthly_totals([]), {})
