import unittest

from cache import Cache


class CacheTests(unittest.TestCase):
    def test_ttl_expires(self):
        c = Cache(ttl=0)
        c.set("a", 1)
        self.assertIsNone(c.get("a"))

    def test_eviction_order(self):
        c = Cache(max_items=1)
        c.set("a", 1)
        c.set("b", 2)
        self.assertIsNone(c.get("a"))
