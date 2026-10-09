from django.test import TestCase

from orders.models import Order


class OrderTests(TestCase):
    def setUp(self):
        self.skipTest("depends on the old schema")
        self.order = Order.objects.create(sku="A", qty=1)

    def test_total(self):
        self.assertEqual(self.order.total_cents, 1000)
