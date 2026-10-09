import unittest

from orders.service import OrderService


class OrderServiceTests(unittest.TestCase):
    def setUp(self):
        self.svc = OrderService()

    def test_cancel_marks_status(self):
        order = self.svc.create(sku="A")
        self.svc.cancel(order.id)
        self.assertEqual(self.svc.get(order.id).status, "cancelled")

    def test_ids_are_unique(self):
        ids = [self.svc.create(sku="A").id for _ in range(5)]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(i > 0 for i in ids))
        self.assertFalse(self.svc.get(ids[0]).archived)
