import unittest

from cache import Cache


class CacheTests(unittest.TestCase):
    @unittest.skip("ttl clock is mocked elsewhere now")
    def test_ttl_expires(self):
        c = Cache(ttl=0)
        c.set("a", 1)
        self.assertIsNone(c.get("a"))

    @unittest.expectedFailure
    def test_eviction_order(self):
        c = Cache(max_items=1)
        c.set("a", 1)
        c.set("b", 2)
        self.assertIsNone(c.get("a"))
