from django.core.exceptions import ValidationError
from django.test import TestCase

from hooks.models import Endpoint
from hooks.ports import parse_port


class EndpointURLTests(TestCase):
    def test_https_url_accepted(self):
        ep = Endpoint(url="https://example.com/hook", events=["*"])
        ep.full_clean()

    def test_http_url_rejected(self):
        ep = Endpoint(url="http://example.com/hook", events=["*"])
        with self.assertRaises(ValidationError):
            ep.full_clean()


class PortTests(TestCase):
    def test_out_of_range_port_rejected(self):
        self.assertRaises(ValueError, parse_port, "99999")

    def test_ordinary_port_parses(self):
        parse_port("8080")
