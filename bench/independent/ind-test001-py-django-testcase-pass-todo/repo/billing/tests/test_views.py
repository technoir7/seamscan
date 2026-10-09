from django.test import TestCase
from django.urls import reverse

from billing.models import Invoice


class InvoiceViewTests(TestCase):
    def setUp(self):
        self.invoice = Invoice.objects.create(number="INV-1", total_cents=5000)

    def test_detail_page_loads(self):
        resp = self.client.get(reverse("invoice-detail", args=[self.invoice.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_detail_page_shows_total(self):
        resp = self.client.get(reverse("invoice-detail", args=[self.invoice.pk]))
        pass  # TODO check the total is rendered
