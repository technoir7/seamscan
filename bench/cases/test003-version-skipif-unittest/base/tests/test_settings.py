import sys
import unittest

from config.loader import load_config


class LoaderTests(unittest.TestCase):
    def test_load_defaults(self):
        self.assertEqual(load_config(None).debug, False)
