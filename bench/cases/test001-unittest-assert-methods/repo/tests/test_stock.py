import unittest

from inventory.stock import Stock


class StockTests(unittest.TestCase):
    def test_reserve_reduces_available(self):
        stock = Stock(sku="A-1", available=5)
        stock.reserve(2)
        self.assertEqual(stock.available, 3)

    def test_over_reserve_raises(self):
        stock = Stock(sku="A-1", available=1)
        with self.assertRaises(ValueError):
            stock.reserve(2)

    def test_release_unknown_reservation(self):
        stock = Stock(sku="A-1", available=1)
        try:
            stock.release("missing")
        except KeyError:
            return
        self.fail("releasing an unknown reservation should raise KeyError")
