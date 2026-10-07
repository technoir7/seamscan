import sys
import unittest

from config.loader import load_config


class LoaderTests(unittest.TestCase):
    def test_load_defaults(self):
        self.assertEqual(load_config(None).debug, False)

    @unittest.skipIf(sys.version_info < (3, 12), "needs 3.12 tomllib behaviour")
    def test_load_toml_with_nested_tables(self):
        self.assertEqual(load_config("nested.toml").db.port, 5432)
